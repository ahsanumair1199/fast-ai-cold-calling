from io import BytesIO
from zipfile import BadZipFile
from fastapi import HTTPException
import pandas as pd
# END IMPORTS


async def validate_excel(file):
    # Check if the file is a valid Excel file
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(
            status_code=400, detail="Invalid file format. Only Excel files are allowed.")
    # Read the Excel file into a DataFrame
    try:
        # Convert the SpooledTemporaryFile to a BytesIO object
        file_contents = await file.read()
        file_bytesio = BytesIO(file_contents)
        df = pd.read_excel(file_bytesio)
        # Validate the columns in the DataFrame
        required_columns = ['first_name', 'last_name', 'email', 'phone']
        if not all(column in df.columns for column in required_columns):
            raise HTTPException(
                status_code=400, detail="Invalid Excel file. Missing required columns.")
        # Check if there are no extra columns
        if set(df.columns) != set(required_columns):
            raise HTTPException(
                status_code=400, detail="Invalid Excel file. Extra columns detected.")
        # Convert DataFrame to a list of dictionaries
        excel_data_list = df.to_dict(orient='records')
        return excel_data_list
    except (pd.errors.ParserError, BadZipFile) as e:
        raise HTTPException(
            status_code=400, detail=f"Error parsing Excel file: Corrupted file")
