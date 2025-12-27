import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import asyncio
from utils import calc_statistic, load_data, check_outlier, fetch_temp_async

def main():
    st.title("Анализ температурных данных и мониторинг текущей температуры через OpenWeatherMap API")

    uploaded_file = st.file_uploader("Загрузите CSV с историческими данными", type=["csv"])
    if uploaded_file:
        df = load_data(uploaded_file)

        city = st.selectbox("Город", sorted(list(df['city'].unique())))

        left_date_bound, right_date_bound, cnt_dates, season_profiles, data = calc_statistic(df, city)

        st.title(f"📊 Описательная статистика для {city}")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            label="📅 Мин. дата",
            value=left_date_bound
        )

        col2.metric(
            label="📅 Макс. дата",
            value=right_date_bound
        )

        col3.metric(
            label="📊 Кол-во уникальных дат",
            value=cnt_dates
        )

        st.title('Визуализация исторических данных')

        fig = px.line(
            data,
            x='timestamp',
            y='temperature',
            labels={
                'timestamp': 'Дата',
                'temperature': 'Температура, °C'
            }
        )

        fig.data[0].update(
            line=dict(
                color='#58a6ff',
                width=1
            ),
            opacity=0.5,
            name='Температура'
        )

        outliers = data[data['is_outlier']]

        fig.add_trace(
            go.Scatter(
                x=outliers['timestamp'],
                y=outliers['temperature'],
                mode='markers',
                name='Выбросы',
                marker=dict(
                    color='#f85149',
                    size=9,
                    symbol='circle'
                )
            )
        )

        fig.add_trace(
            go.Scatter(
                x=data['timestamp'],
                y=data['temperature_30d_rol_mean'],
                mode='lines',
                name='30-дневное среднее',
                line=dict(
                    color='orange',
                    width=2,
                )
            )
        )

        fig.update_layout(
            template="simple_white",
            title=dict(
                text="🌡️ Дневная температура",
                x=0.02,
                font=dict(size=22)
            ),
            height=480,
            hovermode="x unified",
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font=dict(color="#e6edf3"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor='rgba(0,0,0,0.08)')

        st.plotly_chart(fig, use_container_width=True)

        st.title('Сезонные профили')
        st.dataframe(season_profiles)

        st.title("🌤️ Текущая температура через OpenWeatherMap API")
        api_key = st.text_input(
            "Введите API-ключ",
            type="password",
            placeholder="api-key"
        )

        if api_key:
            res = asyncio.run(fetch_temp_async(city, api_key))[0]

            if isinstance(res, dict) and res['cod'] == 401:
                st.error(res)
            else:
                st.success("API-ключ введён корректно")
                temp, feels_like, description = res

                st.title("🌍 Погода сейчас")

                col1, col2 = st.columns(2)

                col1.metric(
                    label="🌡️ Температура",
                    value=f"{temp} °C",
                    delta=f"{temp - feels_like:.1f} °C"
                )

                col2.metric(
                    label="🤔 Ощущается как",
                    value=f"{feels_like} °C"
                )

                st.subheader(description.capitalize())
                
                col1 = st.columns([1, 2])
                is_outlier_current = check_outlier(data, city, temp, pd.to_datetime('today'))
                if is_outlier_current:
                    col2.error("🚨 Температура вне нормы")
                else:
                    col2.success("✅ Температура в пределах нормы")

if __name__ == "__main__":
    main()