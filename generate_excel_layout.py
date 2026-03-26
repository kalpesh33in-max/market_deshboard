
import pandas as pd

# 1. Create Dummy Option Chain Data (Bank Nifty example @ 54000)
atm = 54000
strikes = [atm + (i * 100) for i in range(-5, 6)]

option_chain_data = {
    "Strike": strikes,
    "CE BUY (Lots)": [150, 400, 220, 800, 1200, 2500, 300, 150, 50, 20, 10],
    "CE WRITE (Lots)": [10, 20, 50, 100, 300, 1200, 2800, 3500, 4200, 5000, 6000],
    "PE BUY (Lots)": [5000, 4200, 3500, 2800, 1200, 800, 400, 200, 100, 50, 20],
    "PE WRITE (Lots)": [10, 50, 150, 400, 1500, 3200, 1800, 900, 400, 200, 100],
    "Zone": ["ITM" if s < atm else ("ATM" if s == atm else "OTM") for s in strikes]
}
df_oc = pd.DataFrame(option_chain_data)

# 2. Create Dummy Heavy Activity Data
heavy_activity_data = {
    "Time": ["09:20", "10:15", "11:05", "12:45", "14:10"],
    "Symbol": ["BANKNIFTY54000CE", "HDFCBANK800PE", "SBIN1050CE", "BANKNIFTY54500PE", "ICICIBANK1260FUT"],
    "Action": ["CALL BUY", "PUT WRITER", "SHORT COVERING", "PUT BUY", "FUTURE BUY"],
    "Lots": [2500, 1800, 1500, 1200, 1100],
    "Sentiment": ["BULLISH", "BULLISH", "BULLISH", "BEARISH", "BULLISH"]
}
df_heavy = pd.DataFrame(heavy_activity_data)

# 3. Save to Excel with formatting (using XlsxWriter engine)
file_path = r"C:\Users\kalpe\market_dashboard\dashboard_layout_sample.xlsx"
with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
    # Title & Selection Area
    workbook = writer.book
    worksheet = workbook.add_worksheet('Dashboard')
    writer.sheets['Dashboard'] = worksheet
    
    header_fmt = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#2F75B5', 'border': 1})
    atm_fmt = workbook.add_format({'bg_color': '#FFF2CC', 'bold': True, 'border': 1})
    buy_fmt = workbook.add_format({'font_color': '#006100', 'bg_color': '#C6EFCE'})
    write_fmt = workbook.add_format({'font_color': '#9C0006', 'bg_color': '#FFC7CE'})

    # Write Static Info
    worksheet.write('A1', 'LIVE MARKET SENTIMENT DASHBOARD', workbook.add_format({'bold': True, 'font_size': 14}))
    worksheet.write('A2', 'Selected Asset:', workbook.add_format({'bold': True}))
    worksheet.write('B2', 'BANKNIFTY (Selected from Dropdown)')
    worksheet.write('A3', 'Current Future Price:', workbook.add_format({'bold': True}))
    worksheet.write('B3', 54042.20)

    # Write Option Chain Table
    worksheet.write('A5', 'OPTION CHAIN SENTIMENT (Net Cumulative Lots)', workbook.add_format({'bold': True, 'italic': True}))
    df_oc.to_excel(writer, sheet_name='Dashboard', startrow=5, index=False)
    
    # Write Heavy Activity Table
    worksheet.write('A19', 'HEAVY ACTIVITY / TOP ALERTS', workbook.add_format({'bold': True, 'italic': True}))
    df_heavy.to_excel(writer, sheet_name='Dashboard', startrow=19, index=False)

    # Apply some basic column width
    worksheet.set_column('A:F', 18)

print(f"Excel layout generated at: {file_path}")
