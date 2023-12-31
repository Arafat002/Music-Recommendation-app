import pandas as pd
import numpy as np
import json
import re 
import sys
import itertools
import pyarrow
import ast
from flask import Flask,render_template,request
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")


def createPlaylist(id_list, spotify_df, n):

    idDF = pd.DataFrame({'id':[],'name':[],'artists':[],'url':[],'date_added':[]})
    for id in id_list:
        artistName = spotify_df[spotify_df['id'] == id]['artists_upd_v1'].iloc[0]
        songName = spotify_df[spotify_df['id'] == id]['name'].values[0]
        imageId = spotify_df[spotify_df['id'] == id]['url'].values[0]
        newRow = {'id':id,'name':songName,'artists':artistName,'url':imageId,
        'date_added':pd.to_datetime('2021-04-27 08:09:52+00:00')}
        idDF = idDF.append(newRow,ignore_index=True)

    return idDF



def generate_playlist_feature(complete_feature_set, playlist_df, weight_factor):

    complete_feature_set_playlist = complete_feature_set[complete_feature_set['id'].isin(playlist_df['id'].values)]#.drop('id', axis = 1).mean(axis =0)
    complete_feature_set_playlist = complete_feature_set_playlist.merge(playlist_df[['id','date_added']], on = 'id', how = 'inner')
    complete_feature_set_nonplaylist = complete_feature_set[~complete_feature_set['id'].isin(playlist_df['id'].values)]#.drop('id', axis = 1)
    
    playlist_feature_set = complete_feature_set_playlist.sort_values('date_added',ascending=False)

    most_recent_date = playlist_feature_set.iloc[0,-1]
    
    for ix, row in playlist_feature_set.iterrows():
        playlist_feature_set.loc[ix,'months_from_recent'] = int((most_recent_date.to_pydatetime() - row.iloc[-1].to_pydatetime()).days / 30)
        
    playlist_feature_set['weight'] = playlist_feature_set['months_from_recent'].apply(lambda x: weight_factor ** (-x))
    
    playlist_feature_set_weighted = playlist_feature_set.copy()
    #print(playlist_feature_set_weighted.iloc[:,:-4].columns)
    playlist_feature_set_weighted.update(playlist_feature_set_weighted.iloc[:,:-4].mul(playlist_feature_set_weighted.weight,0))
    playlist_feature_set_weighted_final = playlist_feature_set_weighted.iloc[:, :-4]
    #playlist_feature_set_weighted_final['id'] = playlist_feature_set['id']
    
    return playlist_feature_set_weighted_final.sum(axis = 0), complete_feature_set_nonplaylist


def remove_same_tracks(recos, chosen):

    l = []
    for i in range(50):
        if recos.iloc[i]['id'] in chosen:
            l.append(recos.iloc[i].name)


    recos.drop(l, inplace=True)
    return recos


def generate_playlist_recos(spotify_df, features, feature_set, chosen):

    recos = spotify_df[spotify_df['id'].isin(feature_set['id'].values)]
    recos['sim'] = cosine_similarity(feature_set.drop('id', axis = 1).values, features.values.reshape(1, -1))[:,0]
    recos_top = recos.sort_values('sim',ascending = False).head(50)

    recos_top = remove_same_tracks(recos_top, chosen)
    recos_top = recos_top.drop_duplicates("artists").head(10)
    recos_top['artists'] = recos_top['artists'].apply(ast.literal_eval)
    recos_top['url'] = recos_top['id'].apply(lambda x: spotify_df[spotify_df['id'] == x]['url'].values[0])

    recos_top = recos_top[['id','name','artists','url']]
    
    return recos_top