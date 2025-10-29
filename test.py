from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, HTMLResponse
from starlette.requests import Request
from sqlalchemy import create_engine, MetaData, Table, select, inspect
import pandas as pd
from datetime import datetime
import os
import json

# Создаем подключение к базе данных
DB_PATH = os.path.join(os.path.dirname(__file__), 'databases', 'weather_station.db')
engine = create_engine(f'sqlite:///{DB_PATH}')
metadata = MetaData()

# Получаем список всех таблиц в базе данных
def get_table_names():
    inspector = inspect(engine)
    return inspector.get_table_names()

async def homepage(request: Request):
    """Главная страница - список всех таблиц и API endpoints"""
    table_names = get_table_names()
    
    endpoints_info = {}
    for table_name in table_names:
        endpoints_info[f"/api/{table_name}"] = f"Get data from {table_name} table"
        endpoints_info[f"/api/{table_name}/latest"] = f"Get latest record from {table_name} table"
        endpoints_info[f"/api/{table_name}/stats"] = f"Get statistics for {table_name} table"
        endpoints_info[f"/api/{table_name}/structure"] = f"Get table structure (columns info) for {table_name} table"
    
    return JSONResponse({
        "message": "Weather Station API",
        "available_tables": table_names,
        "endpoints": endpoints_info,
        "examples": {
            "get_all_data": "/api/indoor_sensor?limit=10",
            "get_latest": "/api/indoor_sensor/latest",
            "get_stats": "/api/indoor_sensor/stats",
            "get_structure": "/api/indoor_sensor/structure"
        }
    })

from sqlalchemy import text

async def api_table_all_data(request: Request):
    """API endpoint для получения всех записей из таблицы"""
    try:
        table_name = request.path_params['table_name']
        
        print(f"=== ДЕБАГ ИНФОРМАЦИЯ ===")
        print(f"Запрошенная таблица: {table_name}")
        
        # Проверяем существование таблицы
        available_tables = get_table_names()
        print(f"Доступные таблицы: {available_tables}")
        
        if table_name not in available_tables:
            return JSONResponse({'error': f'Table {table_name} not found. Available: {available_tables}'}, status_code=404)
        
        # Простой способ через pandas
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql(query, engine)
        
        print(f"Количество записей: {len(df)}")
        print(f"Колонки: {df.columns.tolist()}")
        
        # Конвертируем в список словарей
        all_data = df.to_dict('records')
        
        # Конвертируем datetime в строки
        for record in all_data:
            for key, value in record.items():
                if isinstance(value, datetime):
                    record[key] = value.isoformat()
        
        return JSONResponse({
            'table': table_name,
            'data': all_data,
            'total_records': len(all_data),
            'columns': df.columns.tolist()
        })
        
    except Exception as e:
        import traceback
        print(f"Ошибка: {str(e)}")
        print(traceback.format_exc())
        return JSONResponse({'error': str(e)}, status_code=500)

async def html_table_all_data(request: Request):
    """HTML endpoint для отображения всех записей из таблицы в виде красивой HTML таблицы с графиками"""
    try:
        table_name = request.path_params['table_name']
        
        # Проверяем существование таблицы
        available_tables = get_table_names()
        if table_name not in available_tables:
            return HTMLResponse(f"<h1>Ошибка</h1><p>Таблица '{table_name}' не найдена.</p>")
        
        # Получаем данные
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql(query, engine)
        
        # Определяем числовые колонки для графиков
        numeric_columns = []
        datetime_columns = []
        
        for column in df.columns:
            if pd.api.types.is_numeric_dtype(df[column]):
                numeric_columns.append(column)
            elif pd.api.types.is_datetime64_any_dtype(df[column]):
                datetime_columns.append(column)
        
        # Подготавливаем данные для JavaScript
        chart_data = []
        for column in numeric_columns:
            chart_data.append({
                'name': column,
                'values': df[column].fillna(0).tolist(),
                'timestamps': df[datetime_columns[0]].astype(str).tolist() if datetime_columns else list(range(len(df)))
            })
        
        # Генерируем HTML с переключением между таблицей и графиком
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Данные таблицы {table_name}</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 95%;
                    margin: 0 auto;
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    border-bottom: 2px solid #007bff;
                    padding-bottom: 10px;
                }}
                .table-info {{
                    background: #e9ecef;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .view-controls {{
                    margin: 20px 0;
                    display: flex;
                    gap: 10px;
                }}
                .view-btn {{
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                    transition: all 0.3s;
                }}
                .view-btn.active {{
                    background: #007bff;
                    color: white;
                }}
                .view-btn:not(.active) {{
                    background: #e9ecef;
                    color: #333;
                }}
                .view-btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                }}
                .view-content {{
                    margin-top: 20px;
                }}
                .tableView {{
                    overflow-x: auto;
                }}
                .chartView {{
                    display: none;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }}
                th {{
                    background-color: #007bff;
                    color: white;
                    position: sticky;
                    top: 0;
                }}
                tr:nth-child(even) {{
                    background-color: #f8f9fa;
                }}
                tr:hover {{
                    background-color: #e9ecef;
                }}
                .back-link {{
                    display: inline-block;
                    margin-bottom: 20px;
                    color: #007bff;
                    text-decoration: none;
                    font-weight: bold;
                }}
                .back-link:hover {{
                    text-decoration: underline;
                }}
                .timestamp {{
                    font-family: monospace;
                    font-size: 0.9em;
                }}
                .chart-container {{
                    position: relative;
                    height: 500px;
                    margin-bottom: 30px;
                }}
                .chart-controls {{
                    margin: 15px 0;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 5px;
                }}
                .chart-select {{
                    padding: 8px 12px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 14px;
                    margin-right: 10px;
                }}
                .chart-type-select {{
                    padding: 8px 12px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 14px;
                    margin-right: 10px;
                }}
                .no-data {{
                    text-align: center;
                    color: #666;
                    font-style: italic;
                    padding: 40px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <a href="/api/html/tables" class="back-link">← Назад к списку таблиц</a>
                <h1>Таблица: {table_name}</h1>
                
                <div class="table-info">
                    <strong>Всего записей:</strong> {len(df)}<br>
                    <strong>Колонки:</strong> {', '.join(df.columns.tolist())}<br>
                    <strong>Числовые колонки для графиков:</strong> {', '.join(numeric_columns) if numeric_columns else 'нет'}
                </div>

                <div class="view-controls">
                    <button class="view-btn active" onclick="showView('tableView')">Таблица</button>
                </div>

                <div class="view-content">
                    <div id="tableView" class="tableView">
        """
        
        if len(df) > 0:
            html_content += """
                        <div style="overflow-x: auto;">
                        <table>
                            <thead>
                                <tr>
            """
            
            # Заголовки таблицы
            for column in df.columns:
                html_content += f"<th>{column}</th>"
            html_content += "</tr></thead><tbody>"
            
            # Данные таблицы
            for _, row in df.iterrows():
                html_content += "<tr>"
                for value in row:
                    if pd.isna(value):
                        html_content += "<td style='color: #999;'>NULL</td>"
                    elif isinstance(value, datetime):
                        html_content += f"<td class='timestamp'>{value.strftime('%Y-%m-%d %H:%M:%S')}</td>"
                    else:
                        html_content += f"<td>{value}</td>"
                html_content += "</tr>"
            
            html_content += "</tbody></table></div>"
        else:
            html_content += "<p style='text-align: center; color: #666;'>Таблица пуста</p>"
        
        html_content += f"""
                    </div>

                    <div id="chartView" class="chartView">
                        <div class="chart-controls">
                            <label for="chartColumn">Выберите колонку для графика:</label>
                            <select id="chartColumn" class="chart-select" onchange="updateChart()">
        """
        
        # Добавляем опции для выбора колонок
        for column in numeric_columns:
            html_content += f'<option value="{column}">{column}</option>'
        
        html_content += """
                            </select>
                            
                            <label for="chartType">Тип графика:</label>
                            <select id="chartType" class="chart-type-select" onchange="updateChart()">
                                <option value="line">Линейный</option>
                                <option value="bar">Столбчатый</option>
                                <option value="scatter">Точечный</option>
                            </select>
                        </div>
                        
                        <div class="chart-container">
                            <canvas id="dataChart"></canvas>
                        </div>
                        
                        <div id="noChartData" class="no-data" style="display: none;">
                            Нет числовых данных для построения графиков
                        </div>
                    </div>
                </div>
            </div>

            <script>
                const chartData = {json.dumps(chart_data)};
                let currentChart = null;

                function showView(viewName) {{
                    // Скрыть все представления
                    document.querySelectorAll('.view-content > div').forEach(div => {{
                        div.style.display = 'none';
                    }});
                    
                    // Показать выбранное представление
                    document.getElementById(viewName).style.display = 'block';
                    
                    // Обновить активные кнопки
                    document.querySelectorAll('.view-btn').forEach(btn => {{
                        btn.classList.remove('active');
                    }});
                    event.target.classList.add('active');
                    
                    // Если показываем графики, обновляем их
                    if (viewName === 'chartView') {{
                        updateChart();
                    }}
                }}

                function updateChart() {{
                    const selectedColumn = document.getElementById('chartColumn').value;
                    const chartType = document.getElementById('chartType').value;
                    const noDataElement = document.getElementById('noChartData');
                    
                    if (chartData.length === 0) {{
                        noDataElement.style.display = 'block';
                        document.querySelector('.chart-container').style.display = 'none';
                        return;
                    }}
                    
                    noDataElement.style.display = 'none';
                    document.querySelector('.chart-container').style.display = 'block';
                    
                    const columnData = chartData.find(col => col.name === selectedColumn);
                    if (!columnData) return;
                    
                    const ctx = document.getElementById('dataChart').getContext('2d');
                    
                    // Уничтожаем предыдущий график
                    if (currentChart) {{
                        currentChart.destroy();
                    }}
                    
                    // Создаем новый график
                    currentChart = new Chart(ctx, {{
                        type: chartType,
                        data: {{
                            labels: columnData.timestamps,
                            datasets: [{{
                                label: selectedColumn,
                                data: columnData.values,
                                borderColor: '#007bff',
                                backgroundColor: chartType === 'bar' ? 'rgba(0, 123, 255, 0.5)' : 'rgba(0, 123, 255, 0.1)',
                                borderWidth: 2,
                                pointBackgroundColor: '#007bff',
                                pointBorderColor: '#fff',
                                pointBorderWidth: 2,
                                pointRadius: 3,
                                fill: chartType === 'line'
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                title: {{
                                    display: true,
                                    text: `График: ${{selectedColumn}}`
                                }},
                                legend: {{
                                    display: true
                                }}
                            }},
                            scales: {{
                                x: {{
                                    title: {{
                                        display: true,
                                        text: 'Время / Индекс'
                                    }},
                                    ticks: {{
                                        maxTicksLimit: 10,
                                        callback: function(value) {{
                                            // Форматируем timestamp для лучшего отображения
                                            const label = this.getLabelForValue(value);
                                            if (label.includes('T')) {{
                                                const date = new Date(label);
                                                return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                                            }}
                                            return label;
                                        }}
                                    }}
                                }},
                                y: {{
                                    title: {{
                                        display: true,
                                        text: selectedColumn
                                    }}
                                }}
                            }}
                        }}
                    }});
                }}

                // Инициализация при загрузке страницы
                document.addEventListener('DOMContentLoaded', function() {{
                    if (chartData.length === 0) {{
                        document.querySelector('[onclick="showView(\\'chartView\\')"]').disabled = true;
                    }} else {{
                        updateChart();
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(html_content)
        
    except Exception as e:
        import traceback
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Ошибка</title></head>
        <body style="font-family: Arial; margin: 20px;">
            <h1 style="color: #dc3545;">Ошибка при загрузке данных</h1>
            <p><strong>Таблица:</strong> {table_name}</p>
            <p><strong>Ошибка:</strong> {str(e)}</p>
            <pre style="background: #f8f9fa; padding: 15px; border-radius: 5px;">{traceback.format_exc()}</pre>
            <a href="/api/html/tables">← Назад к списку таблиц</a>
        </body>
        </html>
        """
        return HTMLResponse(error_html, status_code=500)

async def api_tables_list(request: Request):
    """API endpoint для получения списка всех таблиц"""
    table_names = get_table_names()
    
    tables_info = []
    for table_name in table_names:
        table = Table(table_name, metadata, autoload_with=engine)
        columns = [{"name": col.name, "type": str(col.type)} for col in table.columns]
        
        tables_info.append({
            'name': table_name,
            'columns': columns,
            'row_count': get_table_row_count(table_name)
        })
    
    return JSONResponse({
        'tables': tables_info,
        'total_tables': len(table_names)
    })

async def html_tables_list(request: Request):
    """HTML endpoint для отображения списка всех таблиц"""
    table_names = get_table_names()
    
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Список таблиц базы данных</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 2px solid #007bff;
                padding-bottom: 10px;
            }
            .stats {
                background: #e9ecef;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .table-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            .table-card {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                background: white;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .table-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }
            .table-card h3 {
                margin-top: 0;
                color: #007bff;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }
            .table-actions {
                margin-top: 15px;
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }
            .btn {
                display: inline-block;
                padding: 8px 16px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-size: 14px;
                transition: background 0.2s;
            }
            .btn:hover {
                background: #0056b3;
            }
            .btn-api {
                background: #28a745;
            }
            .btn-api:hover {
                background: #1e7e34;
            }
            .btn-html {
                background: #17a2b8;
            }
            .btn-html:hover {
                background: #138496;
            }
            .columns-list {
                font-size: 0.9em;
                color: #666;
                max-height: 100px;
                overflow-y: auto;
                background: #f8f9fa;
                padding: 10px;
                border-radius: 4px;
                margin-top: 10px;
            }
            .row-count {
                font-weight: bold;
                color: #495057;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Таблицы базы данных</h1>
                       
            <div class="table-grid">
    """

    for table_name in table_names:
        table = Table(table_name, metadata, autoload_with=engine)
        columns = [col.name for col in table.columns]
        row_count = get_table_row_count(table_name)
        
        html_content += f"""
                <div class="table-card">
                    <h3>{table_name}</h3>
                    <div class="row-count">Записей: {row_count}</div>
                    
                    <div class="columns-list">
                        <strong>Колонки:</strong><br>
                        {', '.join(columns)}
                    </div>
                    
                    <div class="table-actions">
                        <a href="/api/html/{table_name}/all" class="btn btn-html">Просмотр HTML</a>
                        <a href="/api/{table_name}/all" class="btn btn-api">API JSON</a>
                    </div>
                </div>
        """
    
    html_content += """
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 5px;">
                <h3>Доступные endpoints:</h3>
                <ul>
                    <li><strong>API JSON:</strong> <code>/api/table_name</code> - данные с пагинацией</li>
                    <li><strong>API JSON:</strong> <code>/api/table_name/all</code> - все данные</li>
                    <li><strong>API JSON:</strong> <code>/api/table_name/latest</code> - последняя запись</li>
                    <li><strong>API JSON:</strong> <code>/api/table_name/stats</code> - статистика</li>
                    <li><strong>HTML View:</strong> <code>/api/html/table_name/all</code> - HTML просмотр с графиками</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(html_content)

# ... остальные функции (api_table_data, api_table_latest, api_table_stats) остаются без изменений ...

def get_table_row_count(table_name):
    """Вспомогательная функция для получения количества строк в таблице"""
    try:
        table = Table(table_name, metadata, autoload_with=engine)
        with engine.connect() as connection:
            count_query = select([table.c.id]).select_from(table)
            return connection.execute(count_query).rowcount
    except:
        return 0

from starlette.middleware.cors import CORSMiddleware

# Маршруты
routes = [
    Route('/', homepage),
    Route('/api/tables', api_tables_list),
    Route('/api/html/tables', html_tables_list),
    Route('/api/{table_name}', api_table_all_data),
    # Route('/api/{table_name}/latest', api_table_latest),
    # Route('/api/{table_name}/stats', api_table_stats),
    Route('/api/{table_name}/all', api_table_all_data),
    Route('/api/html/{table_name}/all', html_table_all_data),
]

# Создание приложения
app = Starlette(debug=True, routes=routes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)