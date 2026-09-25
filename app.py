"""AmurTrans Control educational order dashboard (CSV only, no backend database)."""
from __future__ import annotations

import base64
import io
from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, State, dash_table, dcc, html
from dash.exceptions import PreventUpdate

HERE = Path(__file__).resolve().parent
REQUIRED = {"order_id", "created_at", "origin", "destination", "status", "carrier", "planned_hours", "actual_hours", "price_rub", "documents_complete"}
STATUSES = ["На согласовании", "Запланирован", "В пути", "Доставлен", "Закрыт"]
COLORS = {"Закрыт": "#237361", "Доставлен": "#71a98b", "В пути": "#e6a33f", "Запланирован": "#82aeb3", "На согласовании": "#a4aaa4"}


def parse_csv(contents: bytes) -> pd.DataFrame:
    if len(contents) > 5_000_000:
        raise ValueError("CSV больше 5 МБ")
    frame = pd.read_csv(io.BytesIO(contents), encoding="utf-8-sig")
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError("Нет столбцов: " + ", ".join(sorted(missing)))
    if len(frame) > 10_000:
        raise ValueError("Слишком много строк (максимум 10 000)")
    frame = frame.copy()
    frame["created_at"] = pd.to_datetime(frame["created_at"], errors="coerce")
    for col in ("planned_hours", "actual_hours", "price_rub"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.dropna(subset=["order_id", "created_at", "status", "planned_hours", "price_rub"])
    frame = frame[frame["status"].isin(STATUSES)]
    frame = frame[(frame["planned_hours"] > 0) & (frame["price_rub"] >= 0)]
    if frame.empty:
        raise ValueError("В CSV нет корректных заказов")
    frame["created_at"] = frame["created_at"].dt.strftime("%Y-%m-%d")
    return frame


INITIAL = parse_csv((HERE / "demo_orders.csv").read_bytes())
app = Dash(__name__, title="АмурТранс Контроль — аналитика")
server = app.server


def chart_style(fig):
    fig.update_layout(template="plotly_white", paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", font_color="#263a34", margin=dict(l=24, r=24, t=54, b=28), legend_title_text="")
    return fig


app.layout = html.Div(className="page", children=[
    dcc.Store(id="orders", data=INITIAL.to_dict("records")),
    html.Header(className="topbar", children=[
        html.Div([html.Div("АТ", className="mark"), html.Div([html.Strong("АмурТранс Контроль"), html.Small("Аналитика транспортных заказов")])], className="brand"),
        html.Span("Учебные демонстрационные данные", className="badge"),
    ]),
    html.Main(children=[
        html.Div(className="intro", children=[html.Div([html.P("ПАНЕЛЬ ПОКАЗАТЕЛЕЙ", className="eyebrow"), html.H1("Что происходит с заказами"), html.P("Загрузите CSV, выберите период и статусы. Графики и таблица обновятся вместе.")]), dcc.Upload(id="upload", className="upload", children="Загрузить CSV · до 5 МБ", accept=".csv")]),
        html.Div(id="upload-message", className="message", children="Открыт демонстрационный набор из 120 заказов."),
        html.Div(className="filters", children=[
            html.Div([html.Label("Период создания"), dcc.DatePickerRange(id="dates", start_date=INITIAL["created_at"].min(), end_date=INITIAL["created_at"].max(), display_format="DD.MM.YYYY")]),
            html.Div([html.Label("Статус"), dcc.Dropdown(id="statuses", options=[{"label": x, "value": x} for x in STATUSES], value=STATUSES, multi=True)]),
            html.Div([html.Label("Перевозчик"), dcc.Dropdown(id="carrier", options=[{"label": "Все перевозчики", "value": "all"}] + [{"label": x, "value": x} for x in sorted(INITIAL["carrier"].unique())], value="all")]),
        ]),
        html.Div(id="metrics", className="metrics"),
        html.Div(className="grid", children=[
            html.Section(className="panel wide", children=[html.H2("Поступление заявок"), dcc.Graph(id="trend")]),
            html.Section(className="panel", children=[html.H2("Структура статусов"), dcc.Graph(id="pie")]),
            html.Section(className="panel", children=[html.H2("Сроки доставки"), dcc.Graph(id="hist")]),
            html.Section(className="panel wide", children=[html.H2("Стоимость и плановый срок"), dcc.Graph(id="scatter")]),
        ]),
        html.Section(className="panel table-panel", children=[html.H2("Реестр заказов"), dash_table.DataTable(id="table", columns=[{"name": name, "id": field} for name, field in [("Заказ", "order_id"), ("Дата", "created_at"), ("Откуда", "origin"), ("Куда", "destination"), ("Статус", "status"), ("Перевозчик", "carrier"), ("План, ч", "planned_hours"), ("Факт, ч", "actual_hours"), ("Стоимость, ₽", "price_rub")]], page_size=10, sort_action="native", filter_action="native", style_table={"overflowX": "auto"}, style_header={"backgroundColor": "#e7eee9", "fontWeight": "700", "color": "#263a34"}, style_cell={"padding": "12px", "fontFamily": "Arial", "textAlign": "left", "borderColor": "#e4ebe6"})]),
        html.P("Данные синтетические. Показатели иллюстрируют проектируемый процесс и не описывают работу реальной компании.", className="footnote"),
    ]),
])


@app.callback(Output("orders", "data"), Output("upload-message", "children"), Output("carrier", "options"), Input("upload", "contents"), State("upload", "filename"), prevent_initial_call=True)
def upload_csv(contents, filename):
    if not contents:
        raise PreventUpdate
    try:
        raw = base64.b64decode(contents.split(",", 1)[1], validate=True)
        frame = parse_csv(raw)
    except (ValueError, UnicodeDecodeError, base64.binascii.Error) as exc:
        return INITIAL.to_dict("records"), f"Ошибка файла: {exc}. Вернулись к демонстрационным данным.", [{"label": "Все перевозчики", "value": "all"}] + [{"label": x, "value": x} for x in sorted(INITIAL["carrier"].unique())]
    options = [{"label": "Все перевозчики", "value": "all"}] + [{"label": x, "value": x} for x in sorted(frame["carrier"].dropna().unique())]
    return frame.to_dict("records"), f"Загружен файл «{filename}»: {len(frame)} корректных заказов.", options


@app.callback(Output("dates", "min_date_allowed"), Output("dates", "max_date_allowed"), Output("dates", "start_date"), Output("dates", "end_date"), Input("orders", "data"))
def update_date_range(data):
    dates = sorted(row["created_at"] for row in data)
    return dates[0], dates[-1], dates[0], dates[-1]


@app.callback(Output("metrics", "children"), Output("trend", "figure"), Output("pie", "figure"), Output("hist", "figure"), Output("scatter", "figure"), Output("table", "data"), Input("orders", "data"), Input("dates", "start_date"), Input("dates", "end_date"), Input("statuses", "value"), Input("carrier", "value"))
def update_view(data, start, end, statuses, carrier):
    frame = pd.DataFrame(data)
    if start:
        frame = frame[frame["created_at"] >= start[:10]]
    if end:
        frame = frame[frame["created_at"] <= end[:10]]
    frame = frame[frame["status"].isin(statuses or [])]
    if carrier and carrier != "all":
        frame = frame[frame["carrier"] == carrier]
    completed = frame[frame["status"].isin(["Доставлен", "Закрыт"])].copy()
    timely = ((completed["actual_hours"] <= completed["planned_hours"]).mean() * 100) if not completed.empty else 0
    cards = [("Заказов", f"{len(frame)}"), ("Доставлено", f"{len(completed)}"), ("В срок", f"{timely:.0f}%" if len(completed) else "—"), ("С документами", f"{(frame['documents_complete'] == 'Да').sum()}")]
    metrics = [html.Div([html.Span(label), html.Strong(value)], className="metric") for label, value in cards]
    monthly = frame.assign(month=frame["created_at"].str.slice(0, 7)).groupby("month").size().reset_index(name="orders")
    trend = chart_style(px.line(monthly, x="month", y="orders", markers=True, labels={"month": "Месяц", "orders": "Заявки"}, color_discrete_sequence=["#237361"]))
    pie = chart_style(px.pie(frame, names="status", color="status", color_discrete_map=COLORS, hole=.55))
    hist = chart_style(px.histogram(completed, x="actual_hours", nbins=12, labels={"actual_hours": "Фактический срок, ч", "count": "Заказы"}, color_discrete_sequence=["#237361"]))
    hist.update_yaxes(title_text="Заказы")
    scatter = chart_style(px.scatter(frame, x="planned_hours", y="price_rub", color="status", hover_data=["order_id", "origin", "destination"], color_discrete_map=COLORS, labels={"planned_hours": "Плановый срок, ч", "price_rub": "Стоимость, ₽", "status": "Статус"}))
    return metrics, trend, pie, hist, scatter, frame.to_dict("records")


app.index_string = app.index_string.replace("</head>", '<link rel="stylesheet" href="/assets/style.css"></head>')

if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8050)
