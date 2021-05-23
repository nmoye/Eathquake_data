#!/usr/bin/env python
# coding: utf-8

# In[2]:


#import packages 
import pandas as pd
import geopandas as gpd
import json
import requests
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import cartopy.crs as ccrs
import shapely.wkt


# In[ ]:


#Range to extract data
x = 1980
j = x + 1
for k in range (x,2021):
    base_url = 'https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime='
    df_list = []
    for i in range (1,13):
        url2 = base_url + f'{k}-%02d-01&endtime={k}-%02d-01&minmagnitude=2.5' % (i, i+1)
        if i == 12:
            url2 = base_url + f'{k}-%02d-01&endtime={j}-01-01&minmagnitude=2.5' % (i)
        #print(url2)
        r2 = requests.get(url2)
        #print(r2.text)
        data = json.loads(r2.text)
        #print(data)
        crs = {'init': 'epsg:4326'}
        gdf = gpd.GeoDataFrame.from_features(data, crs=crs)
        df_list.append(gdf)
        print(url2, 'Finished!')
print(df_list)
#Then, concatenate the data:
full_gdf = pd.concat(df_list, ignore_index=True) 


# In[3]:


#save to csv and read the data
full_gdf.to_csv('USGS_Quakes_1980-2021.csv')
df = pd.read_csv('USGS_Quakes_1980-2021.csv',usecols =['geometry','mag'])
geom = [shapely.wkt.loads(wkt) for wkt in df.geometry.values]
gdf = gpd.GeoDataFrame(df,crs ='epsg:4326', geometry=geom)
del df


# In[4]:


gdf.head()


# In[5]:


#Load Populated places 
places = 'ne_10m_populated_places/ne_10m_populated_places.shp'
places_gdf = gpd.read_file(places)
places_gdf = places_gdf[['NAME', 'geometry']]
places_gdf.head()


# In[6]:


#Buffer populated places 
radius = 0.5
places_gdf['geometry'] = places_gdf.geometry.buffer(radius)
places_gdf.head()


# In[7]:


#Joining all the points in the buffer 
points_in_city = gpd.sjoin(gdf, places_gdf, how='inner', op='intersects')


# In[12]:


#using groupby based on the index of the point
counts = points_in_city.groupby([points_in_city.index]).count()['NAME'].values
mags = points_in_city.groupby([points_in_city.index]).sum()['mag'].values
print(counts.shape, places_gdf.shape)


# In[13]:


#subset of data >5
points_in_city = gpd.sjoin(gdf[gdf.mag >= 5], places_gdf, how ='right', op='intersects')
counts5 = points_in_city.groupby([points_in_city.index]).count()['NAME'].values
mags5 = points_in_city.groupby([points_in_city.index]).sum()['mag'].values
print(counts5.shape,mags5.shape)


# In[14]:


places_gdf['fcount'] = counts
places_gdf['mag']= mags
places_gdf['fcount5']= counts5
places_gdf['mag5'] = mags5

places_gdf= places_gdf.sort_values(by ='fcount', axis=0)

import matplotlib.pyplot as plt
f,ax = plt.subplots(1,figsize=(15,8))
a = ax.scatter(places_gdf.geometry.centroid.x,places_gdf.geometry.centroid.y, c=places_gdf.fcount, vmin=15, vmax=100)
plt.colorbar(a,ax=ax, extend='both')
plt.title('1980-2020 Earthquake Density Map')
plt.savefig('Earthquake_Magnitude.png', dpi=300)
places_gdf.head()


# In[15]:


#Biggest earthquake
ind = (-places_gdf.mag5).argsort()[:10]
print('Biggest:',[places_gdf.iloc[ind]['NAME'].values, places_gdf.iloc[ind]['mag'].values])

#Most Frequent Region
ind = (-places_gdf.fcount5).argsort()[:10]
print('Most Frequent:',[places_gdf.iloc[ind]['NAME'].values, places_gdf.iloc[ind]['fcount'].values])


# In[16]:


#Gridded Maps
import numpy as np
minX, maxX, minY, maxY, width = -180, 0, 0, 60, 0.25
Xspace = np.arange(minX, maxX + width, width)
Yspace = np.arange(minY, maxY + width, width)

from shapely.geometry import Polygon
boxlist = []
for i, xval in enumerate(Xspace[:-1]):
    for j, yval in enumerate(Yspace[:-1]):
        box = [xval, Xspace[i+1], yval, Yspace[j+1]]
        #print(box)
        box_coords = [[box[0], box[2]], [box[1], box[2]], [box[1], box[3]], [box[0], box[3]]]
        #print(box_coords)
        geom = Polygon([[p[0], p[1]] for p in box_coords])
        boxlist.append(geom)
boxes= gpd.GeoDataFrame(crs='epsg:4326', geometry=boxlist)
        


# In[17]:


#spatial Join using boxes
quake_in_box = gpd.sjoin(gdf, boxes, how='right', op='within') 


# In[18]:


mags= quake_in_box.groupby([quake_in_box.index]).sum()['mag'].values


# In[20]:


arr = mags.reshape((Xspace.shape[0]-1, Yspace.shape[0]-1)).T

arr = arr[::-1, :].astype(float)
arr[arr < 1] = np.nan

plt.figure(figsize=(15,10))
plt.imshow(arr, cmap=plt.cm.seismic,norm=LogNorm())
plt.colorbar()
plt.title('Total Magnitude of earthquakes')
plt.savefig('Magnitude of Earthquake', dpi=300)


# In[ ]:




