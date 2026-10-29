# Nassau Candy: Factory Reallocation Dashboard

An interactive Streamlit dashboard for the Factory Reallocation & Shipping Optimization project.
It rebuilds your notebook's analysis from the CSV files, so every number comes from your data.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data

Your project CSV files are already inside the `data` folder, so the dashboard opens straight away with no upload step.

## What is inside

- **Overview**: sales, profit, units, orders, trend, ship modes, product table
- **Factory network**: map of destinations and factories, distance now vs nearest factory
- **Reallocation scenarios**: ranked scenarios with adjustable weights, drill-down map, CSV download
- **What-if simulator**: choose which factories may make a product and see how the average trip changes
- **Demand clusters**: K-Means groups with silhouette chart
- **Recommendations**: top moves to look at, where the avoidable distance is, a suggested plan, downloadable list
- **Data quality**: the ship-date problem, data checks, method and limits

All filters in the sidebar apply to every tab.
