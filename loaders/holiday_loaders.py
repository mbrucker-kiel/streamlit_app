import requests
import pandas as pd
 

def get_holidays(db=None, limit=10000):
    """Fetch holiday data from a public API and return as a DataFrame""" 
    try:
        # Fetch holiday data from the public API
        response = requests.get("https://get.api-feiertage.de/?states=sh")
        response.raise_for_status()  # Raise an error for bad responses
        holidays = response.json()
        # the holidays are nested in a "feiertage" array
        # inside the feiertage array there are all holidays with date/name
        holidays = holidays.get("feiertage", [])
        
        # Process the data into a DataFrame
        records = []
        for holiday in holidays:
            records.append({
                "date": holiday.get("date"),
                "name": holiday.get("fname"),
            })

        df = pd.DataFrame(records)

        return df

    except Exception as e:
        print(f"Error loading holiday data: {e}")
        return pd.DataFrame()
