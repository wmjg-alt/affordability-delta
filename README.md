# The Affordability Delta

An interactive visualization mapping the gap between actual US renter incomes and the reality of the rental market across 33,000+ US ZIP codes. 

**[Live Map Here](https://wmjg-alt.github.io/affordability-delta/)**

## The Math
This map highlights the difference between what renters *should* be paying (the 30% Rule) and what they *are* paying.
`Delta = (Median Renter Income / 12 * 0.30) - Median Gross Rent`
* **Blue:** Rent is below the 30% threshold (Affordable)
* **Red:** Rent is above the 30% threshold (Unaffordable)

## Data Sources
* **Incomes & Rent:** US Census Bureau API (2022 ACS 5-Year Estimates)
* **Map Boundaries:** US Census Bureau Cartographic Boundary Files (2020 ZCTAs)

## How to Run Locally
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Fetch the data: `python fetch_data.py`
4. Build the map: `python build_map.py`
5. Open `index.html` in your web browser.
