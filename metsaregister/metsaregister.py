# -*- coding: utf-8 -*-

import re
import warnings
from collections import OrderedDict
from time import sleep

import geopandas as gpd
import pandas as pd
import pygeoif.geometry
import requests
import shapely.wkt
import xmltodict
from babel.numbers import parse_decimal
from bs4 import BeautifulSoup
from lxml import etree
from retrying import retry
from six import StringIO
from six.moves.urllib.parse import unquote, urljoin
from tqdm import tqdm

species_codes = {
    # Trees
    'MA': 'mänd',
    'KU': 'kuusk',
    'NU': 'nulg',
    'LH': 'lehis',
    'SD': 'seedermänd',
    'TS': 'ebatsuuga',
    'TA': 'tamm',
    'SA': 'saar',
    'VA': 'vaher',
    'JA': 'jalakas',
    'KP': 'künnapuu',
    'KS': 'kask',
    'HB': 'haab',
    'LM': 'sanglepp',
    'LV': 'hall lepp',
    'PN': 'pärn',
    'PP': 'pappel',
    'RE': 'remmelgas',
    'TM': 'toomingas',
    'PI': 'pihlakas',
    'TO': 'teised okaspuuliigid',
    'TL': 'teised lehtpuuliigid',
    # Bushes
    'PA': 'paju',
    'SP': 'sarapuu',
    'TM': 'toomingas',
    'PI': 'pihlakas',
    'PK': 'paakspuu',
    'TY': 'türnpuu',
    'KL': 'kuslapuu',
    'KD': 'kadakas',
    'TP': 'teised põõsaliigid'
}

session = requests.Session()

session.headers.update({
    'Pragma': 'no-cache',
    'Origin': 'http://register.metsad.ee',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.8,et;q=0.6',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': '*/*',
    'Cache-Control': 'no-cache',
    'X-Requested-With': 'ShockwaveFlash/26.0.0.131',
    'Connection': 'keep-alive',
    'Referer': 'http://register.metsad.ee/avalik/flash/map.swf',
})


def get_layers():
    """Returns the list of available layers as a dictionary of layer name -> layer ID."""
    layers = OrderedDict()
    r = session.get("http://register.metsad.ee/avalik/flashconf.php?in=layers")
    r.raise_for_status()
    if 'Error' in r.text:
        raise RuntimeError('Server raised an error: ' + r.text[:1000])
    root = etree.fromstring(r.content)
    for layer in root.xpath('//layer'):
        layers[layer.get('name')] = int(layer.get('Lid'))
    return layers


@retry(wait_exponential_multiplier=1000, stop_max_delay=30000)
def query_layer(aoi, layer_id=10):
    """
    Return the features of the given layer that intersect with the given area of interest.

    Parameters
    ----------
    aoi : str
        A WKT string specifying the area of interest.
    layer_id
        ID number of the layer.

    Returns
    -------
    geopandas.GeoDataFrame
    """
    params = [('in', 'objects'),
              ('layer_id', str(layer_id)),
              ('operation', 'fw')]
    data = [('requestArea', aoi.upper()),
            ('srs', 'EPSG:3301')]
    r = session.post('http://register.metsad.ee/avalik/flashconf.php', params=params, data=data)
    r.raise_for_status()
    if 'Error' in r.text:
        raise RuntimeError('Server raised an error: ' + r.text[:1000])

    crs = {'init': 'epsg:3301'}
    if ">0 objects<" in r.text:
        return gpd.GeoDataFrame(crs=crs)
    features = xmltodict.parse(r.text)['objects']['obj']
    if not isinstance(features, list):
        features = [features]
    df = pd.DataFrame(features).set_index('@id')
    df.index.name = 'id'
    if '@label' in list(df):
        df = df.drop('@label', axis=1)
    if 'url' in list(df):
        df.loc[df['url'].notnull(), 'url'] = df['url'].dropna().map(unquote)

    geometries = []
    for wkt in df['wkt']:
        if wkt.startswith('GEOMETRYCOLLECTION'):
            # GeometryCollection type seems to be more of a bug in the dataset
            # With erroneous LineString objects appearing inside it.
            # It's better to convert it to a MultiPolygon.
            wkt = (re.sub(r'LINESTRING\s*\(([^)]+\))(?:,\s*)?', '', wkt)
                   .replace('POLYGON', '')
                   .replace('GEOMETRYCOLLECTION', 'MULTIPOLYGON'))
        try:
            geometries.append(shapely.wkt.loads(wkt))
        except:
            # A workaround for cases like
            # IllegalArgumentException: Points of LinearRing do not form a closed linestring
            # that Shapely refuses to handle.
            geometries.append(
                shapely.geometry.geo.shape(pygeoif.geometry.from_wkt(wkt))
            )
    df = df.drop('wkt', axis=1)
    gdf = gpd.GeoDataFrame(df, crs=crs, geometry=geometries)
    return gdf


@retry(wait_exponential_multiplier=1000, stop_max_delay=30000)
def get_info(url):
    """Fetch the content of a feature's information page."""
    if 'metsad.ee' not in url:
        url = urljoin('http://register.metsad.ee/avalik/', url)
    r = session.get(url)
    r.raise_for_status()
    txt = r.text
    if 'Error' in txt:
        raise RuntimeError('Server raised an error: ' + r.text[:1000])
    txt = txt.replace('\r\n', '\n').strip()
    txt = re.sub('\s*<script[^>]*>.+</script>\s*', '', txt, flags=re.DOTALL)
    txt = txt.replace("""
	<tr>
		<th colspan="2" id="grpHeader"><a class="button1" href="#"
			onclick="window.print();"><span>Prindi</span></a></th>
	</tr>""", "")
    txt = txt.replace(' onload="resizeWinTo(\'content\');"', '')
    return txt


def _extract_tables(info):
    soup = BeautifulSoup(info, "lxml")
    tables = soup.find_all('table')
    for th in soup.find_all('th'):
        # Remove unnecessary headers
        if th.get('colspan') == '2':
            th.extract()
    for tbl in tables[::-1]:
        # Make nested tables independent
        tbl.extract()
    return tables


def parse_full_inventory_info(info):
    tables = _extract_tables(info)
    txt = tables[0].text
    d = OrderedDict()
    d['Katastritunnus'] = re.search(r'katastritunnus ([^,\s]+)', txt).group(1)
    d['Eraldise nr.'] = int(re.search(r'eraldis ([^,\s]+)', txt).group(1))
    m = re.search(r'kvartal ([^,\s]+)', txt)
    if m:
        d['Kvartali nr.'] = m.group(1)
    else:
        d['Kvartali nr.'] = '-'
    for l in txt.splitlines():
        l = l.strip()
        l = re.sub(r'\s+', ' ', l)
        parts = l.split(': ', 1)
        if len(parts) != 2:
            continue
        key = parts[0]
        value = parts[1].replace(' ha', '')
        try:
            value = float(parse_decimal(value, 'et_ee'))
        except:
            pass
        if 'pindala' in key.lower():
            key += ' (ha)'
        d[key] = value
    s = pd.Series(d)
    s['Täiskirjeldusega'] = True

    kooslus = pd.read_html(StringIO(str(tables[2])), header=0, thousands=' ', decimal=',')[0]
    kooslus = kooslus.loc[kooslus['Rinne'].str.endswith('Esimene')]
    s['Pealiik'] = kooslus.loc[kooslus['%'].idxmax(), 'Puuliik'].lower()
    s['Kõrgus'] = (kooslus['H'] * kooslus['%']).sum() / 100
    s['Vanus'] = (kooslus['Vanus'] * kooslus['%']).sum() / 100
    for idx, row in kooslus.iterrows():
        liik = row['Puuliik'].lower()
        s[liik + ' %'] = row['%']
        s[liik + ' H'] = row['H']
        s[liik + ' A'] = row['Vanus']

    return s


def parse_short_inventory_info(info):
    """
    Parse the information returned for forest stands.
    Returns the main information for the stands and the information of the first tree level by species.

    Parameters
    ----------
    info : str
        The HTML content of forest stand's information page

    Returns
    -------
    pandas.Series
    """
    tables = _extract_tables(info)
    s = (pd.read_html(StringIO(str(tables[0])), thousands=' ', decimal=',')[0]
         .set_index(0)
         .iloc[:, 0])
    s.name = None
    s.index.name = None
    s['Täiskirjeldusega'] = False

    if len(tables) == 1:
        return s
    kooslus = pd.read_html(StringIO(str(tables[1])), header=0, thousands=' ', decimal=',')[0]
    if len(kooslus) == 0:
        return s
    s['Pealiik'] = species_codes[kooslus.loc[kooslus['%'].idxmax(), 'Liik']]
    s['Kõrgus'] = (kooslus['H'] * kooslus['%']).sum() / 100
    s['Vanus'] = (kooslus['A'] * kooslus['%']).sum() / 100
    for idx, row in kooslus.iterrows():
        liik = species_codes[row['Liik']]
        s[liik + ' %'] = row['%']
        s[liik + ' H'] = row['H']
        s[liik + ' A'] = row['A']

    return s


def parse_inventory_info(info):
    """
    Parse the information returned for forest stands (eraldised).
    Returns the main information for the stands and the information of the first tree level by species.

    Parameters
    ----------
    info : str
        The HTML content of forest stand's information page

    Returns
    -------
    pandas.Series
    """
    if u'Üldised takseerandmed' in info:
        return parse_short_inventory_info(info)
    else:
        return parse_full_inventory_info(info)


def parse_forest_notifications(info):
    """
    Parse the information returned for a forest notifications (metsateatised) polygon.
    Only the information regarding this single polygon is returned rather than the full list
    provided in the forest notification.

    Parameters
    ----------
    info : str
        The HTML content of forest notification's information page

    Returns
    -------
    pandas.Series
    """
    tables = _extract_tables(info)
    general_s = (pd.read_html(StringIO(str(tables[0])), thousands=' ', decimal=',')[0]
                 .set_index(0)
                 .iloc[:, 0])
    for row in tables[1].find_all('tr'):
        # Extract the single highlighted row
        if row.get('class') != ['selected_row'] and not row.find('th'):
            row.extract()
    works_s = (pd.read_html(StringIO(str(tables[1])), header=0, thousands=' ', decimal=',',
                            converters={'Kvartal': lambda x: x})[0]
               .iloc[0])
    # Make the Töö field more useful by extracting the amount and number of seed trees left
    work = works_s['Töö']
    works_s['Maht (tm)'] = float('nan')
    works_s['Seemnepuid'] = float('nan')
    if ' tm' in work:
        m = re.search(r'(\D+) +(\d+) +tm(?: +\(seemnepuud +(\d+) +tk\))?', work)
        work_type, amount, seed_trees = m.groups()
        works_s['Töö'] = work_type
        works_s['Maht (tm)'] = float(amount)
        if seed_trees:
            works_s['Seemnepuid'] = float(seed_trees)

    # Avoid abbreviations
    works_s.rename({'Er': 'Eraldis', 'P': 'Pindala (ha)'}, inplace=True)

    return general_s.append(works_s)


def _query_with_info(layer_ids, aoi, parser, wait):
    dfs = []
    for id in layer_ids:
        dfs.append(query_layer(aoi, id))
    df = pd.concat(dfs)
    if df.shape[0] == 0:
        return df
    infos = {}
    for id, url in tqdm(list(df.url.iteritems())):
        txt = get_info(url)
        infos[id] = parser(txt)
        sleep(wait)
    info_df = pd.concat(infos.values(), axis=1).transpose()
    info_df.index = list(infos)
    info_df[info_df == '-'] = float('nan')
    merged = df.join(info_df)
    merged.index.name = 'id'
    merged.reset_index().drop(['url'], axis=1)
    with warnings.catch_warnings():
        # Not converting the numeric values from objects to numeric will cause issues when
        # writing the GeoDataFrame to file.
        # There is no good substitute for the deprecated convert_objects() right now.
        # A future pandas release will have a suitable .infer_objects() method.
        warnings.simplefilter("ignore", category=DeprecationWarning)
        merged = merged.convert_objects()
    return merged


def query_forest_stands(aoi, wait=0.5):
    """Retrieves the forest stands (eraldised) and their information as a GeoDataFrame.

    Parameters
    ----------
    aoi : str
        A WKT string of the area of interest.
    wait : float
        Time to wait between running a subquery for each forest stand. This acts as a rate limit
        to not overly stress the server.

    Returns
    -------
    geopandas.GeoDataFrame
    """
    layer_ids = [
        11,  # Eraldised Eramets: osaline kirjeldus
        14,  # Eraldised Eramets: täiskirjeldus
        12  # Eraldised RMK
    ]
    return _query_with_info(layer_ids, aoi, parse_inventory_info, wait)


def query_forest_notifications(aoi, wait=0.5):
    """Retrieves the forest notifications (metsateatised) and their information as a GeoDataFrame.

    Parameters
    ----------
    aoi : str
        A WKT string of the area of interest.
    wait : float
        Time to wait between running a subquery for each forest stand. This acts as a rate limit
        to not overly stress the server.

    Returns
    -------
    geopandas.GeoDataFrame
    """
    return _query_with_info([10], aoi, parse_forest_notifications, wait)
