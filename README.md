# Nassau Candy Factory Reallocation & Shipping Optimization Dashboard

A beginner-friendly Streamlit dashboard for your Nassau Candy project. It reads the CSV exports from your Colab/Python analysis.

## Files expected

Put these CSV files in the same folder as `app.py`:

- `factory_orders.csv` (required): order-level data, including the `Factory` column if available.
- `priority_scenarios.csv` (optional): product/factory reallocation ranking.
- `distance_analysis.csv` (optional): order-level current and nearest-factory distances.

You can also upload each CSV from the dashboard sidebar, so you do not have to rename or move files.

## Run in VS Code on Windows

1. Download and extract the ZIP.
2. Open the extracted folder in VS Code: **File → Open Folder**.
3. Open **Terminal → New Terminal**.
4. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

5. Start the dashboard:

   ```powershell
   python -m streamlit run app.py
   ```

6. Open the local URL shown in the terminal, usually `http://localhost:8501`.

If `python` is not recognized, install Python from python.org and select **Add Python to PATH** during installation. Restart VS Code after installing.

## CSVs from Google Colab

In Colab, use the left Files panel to download each CSV to your computer. Then either copy them beside `app.py` or upload them using the Streamlit dashboard sidebar.

## Important interpretation notes

- Check the date-quality tab before using shipping lead-time results. Earlier analysis found suspicious ship dates far beyond order dates.
- Distances are straight-line estimates, not actual road or carrier routes.
- Scenario scores are prioritization aids, not guaranteed savings or final factory decisions. Confirm factory capacity, product eligibility, stock, service levels, and actual transport costs before implementing changes.
