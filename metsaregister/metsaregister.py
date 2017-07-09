# -*- coding: utf-8 -*-

import re
from collections import OrderedDict

import geopandas as gpd
import pandas as pd
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

liigikoodid = {
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


def get_layers():
    """Returns the list of available layers as a dictionary of layer name -> layer ID."""
    layers = OrderedDict()
    layers_xml = requests.get("http://register.metsad.ee/avalik/flashconf.php?in=layers").content
    root = etree.fromstring(layers_xml)
    for layer in root.xpath('//layer'):
        layers[layer.get('name')] = layer.get('Lid')
    return layers


@retry(wait_exponential_multiplier=1000, wait_exponential_max=60000)
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
    headers = {
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
    }

    params = {'in': 'objects',
              'layer_id': str(layer_id),
              'operation': 'fw'}

    data = {'requestArea': aoi,
            'srs': 'EPSG:3301'}

    r = requests.post('http://register.metsad.ee/avalik/flashconf.php', headers=headers, params=params, data=data)
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
        df['url'] = df['url'].map(unquote)
    geometry = df['wkt'].map(shapely.wkt.loads)
    df = df.drop('wkt', axis=1)
    gdf = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)
    return gdf


@retry(wait_exponential_multiplier=1000, wait_exponential_max=60000)
def get_info(url):
    """Fetch the content of a feature's information page."""
    if 'metsad.ee' not in url:
        url = urljoin('http://register.metsad.ee/avalik/', url)
    txt = requests.get(url).text
    txt = txt.replace('\r\n', '\n').strip()
    txt = re.sub('\s*<script[^>]*>.+</script>\s*', '', txt, flags=re.DOTALL)
    txt = txt.replace("""
	<tr>
		<th colspan="2" id="grpHeader"><a class="button1" href="#"
			onclick="window.print();"><span>Prindi</span></a></th>
	</tr>""", "")
    txt = txt.replace(' onload="resizeWinTo(\'content\');"', '')
    return txt


def parse_full_takseer(info):
    soup = BeautifulSoup(info, "lxml")
    tables = soup.find_all('table')
    for tbl in tables[::-1]:
        # Make nested tables independent
        tbl.extract()
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


def parse_short_takseer(info):
    soup = BeautifulSoup(info, "lxml")
    tables = soup.find_all('table')
    for th in soup.find_all('th'):
        if th.get('colspan') == '2':
            th.extract()
    for tbl in tables[::-1]:
        # Make nested tables independent
        tbl.extract()
    s = pd.read_html(StringIO(str(tables[0])), thousands=' ', decimal=',')[0].set_index(0).iloc[:, 0]
    s.name = None
    s.index.name = None
    s['Täiskirjeldusega'] = False

    if len(tables) == 1:
        return s
    kooslus = pd.read_html(StringIO(str(tables[1])), header=0, thousands=' ', decimal=',')[0]
    if len(kooslus) == 0:
        return s
    s['Pealiik'] = liigikoodid[kooslus.loc[kooslus['%'].idxmax(), 'Liik']]
    s['Kõrgus'] = (kooslus['H'] * kooslus['%']).sum() / 100
    s['Vanus'] = (kooslus['A'] * kooslus['%']).sum() / 100
    for idx, row in kooslus.iterrows():
        liik = liigikoodid[row['Liik']]
        s[liik + ' %'] = row['%']
        s[liik + ' H'] = row['H']
        s[liik + ' A'] = row['A']

    return s


def parse_takseer(info):
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
    if u'Üldised takseerandmed' in info:
        return parse_short_takseer(info)
    else:
        return parse_full_takseer(info)


def query_forest_stands(aoi):
    """Retrieves the forest stands and their information as a GeoDataFrame.

    Parameters
    ----------
    aoi : str
        A WKT string of the area of interest.

    Returns
    -------
    geopandas.GeoDataFrame
    """
    layer_ids = [
        11,  # Eraldised Eramets: osaline kirjeldus
        14,  # Eraldised Eramets: täiskirjeldus
        12  # Eraldised RMK
    ]

    dfs = []
    for id in layer_ids:
        dfs.append(query_layer(aoi, id))
    df = pd.concat(dfs)
    infos = {}
    for id, url in tqdm(list(df.url.iteritems())):
        txt = get_info(url)
        infos[id] = parse_takseer(txt)
    info_df = pd.concat(infos.values(), axis=1).transpose()
    info_df.index = list(infos)
    info_df[info_df == '-'] = float('nan')
    merged = df.join(info_df)
    merged.index.name = 'id'
    merged.reset_index().drop(['url'], axis=1)
    return merged
