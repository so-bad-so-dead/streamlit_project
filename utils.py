import streamlit as st
import pandas as pd
import asyncio
import httpx

@st.cache_data  # Кэшируем загруженные данные
def load_data(uploaded_file):
    return pd.read_csv(uploaded_file)

async def get_temperature_async(client, city, api_key, print_output=True):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "lang": "ru"
    }

    response = await client.get(url, params=params)
    data = response.json()

    if response.status_code == 200:
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        description = data["weather"][0]["description"]
        if print_output:
            print(f"{city}: {temp}°C")
        return temp, feels_like, description
    else:
        print("Ошибка:", data)
        return data

async def fetch_temp_async(city, api_key):
    async with httpx.AsyncClient() as client:
        tasks = [get_temperature_async(client, city, api_key)]
        results = await asyncio.gather(*tasks)
        
    return results

def mark_outliers(data):
    df_copy = data.copy()
    df_copy['is_outlier'] = (
        (df_copy['temperature'] < df_copy['temperature_30d_rol_mean'] - 2 * df_copy['temperature_std']) |
        (df_copy['temperature'] > df_copy['temperature_30d_rol_mean'] + 2 * df_copy['temperature_std'])
    )
    return df_copy

def calc_statistic(df_data, city):
    data = df_data.query('city == @city').copy()
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data = data.sort_values('timestamp')

    df_30d_roll_temp = (
        data
        .set_index('timestamp')
        .groupby(['city'])['temperature']
        .rolling('30D', min_periods=1)
        .mean()
        .reset_index()                        
    )
    df_30d_roll_temp = df_30d_roll_temp.rename(columns={'temperature': 'temperature_30d_rol_mean'})

    data = data.merge(df_30d_roll_temp, on=['city', 'timestamp'], how='left')

    df_mean_std = (
        data.groupby(['city', 'season'], as_index=False)
        .agg(temperature_mean=('temperature', 'mean'),
            temperature_std=('temperature', 'std'))
    )

    data = data.merge(df_mean_std, on=['city', 'season'], how='left')

    data = mark_outliers(data)

    left_date_bound = data['timestamp'].min().strftime('%Y-%m-%d')
    right_date_bound = data['timestamp'].max().strftime('%Y-%m-%d')
    cnt_dates = data['timestamp'].nunique()

    season_profiles = (
        data
        [['season', 'temperature_mean', 'temperature_std']]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    return left_date_bound, right_date_bound, cnt_dates, season_profiles, data

# Определение, является ли текущая температура аномальной
def get_season(date):
    '''Определение сезона по дате'''
    month = date.month
    if month in (12, 1, 2):
        return "winter"
    elif month in (3, 4, 5):
        return "spring"
    elif month in (6, 7, 8):
        return "summer"
    else:
        return "autumn"

def check_outlier(data, city, temperature, date):
    '''Проверка на аномальность температуры'''
    season = get_season(date)
    temp_mean, temp_std = (
        data[(data['city'] == city) & (data['season'] == season)]
        [['temperature_mean', 'temperature_std']].values[0]
    )
    if (temperature < temp_mean - 2 * temp_std) or (temperature > temp_mean + 2 * temp_std):
        return True
    return False