import json
import pandas as pd
from db import AzureSQLConnection
import os
from dotenv import load_dotenv

load_dotenv()

def load_maps():
    # read all your mapping CSVs from data/
    sex_map = pd.read_csv("data/sex.csv", dtype=str).set_index("Key")["Value"].to_dict()
    age_map = pd.read_csv("data/age.csv", dtype=str).set_index("Key")["Value"].to_dict()
    region_map = pd.read_csv("data/ben_reg.csv", dtype=str).set_index("Key")["Value"].to_dict()
    presc_map = pd.read_csv("data/prescribers.csv", dtype=str).set_index("Key")["Value"].to_dict()
    cpi_map = pd.read_csv("data/cpi.csv", dtype=str).set_index("Key")["Value"].to_dict()
    return sex_map, age_map, region_map, presc_map, cpi_map

def prepare_unified(df: pd.DataFrame, product_type: str) -> pd.DataFrame:
    """
    Standardize brand vs generic DataFrame:
    - Rename product code column to 'product_code'
    - Add 'product_type' column
    """
    df = df.copy()
    if 'CIP13' in df.columns:
        df = df.rename(columns={'CIP13': 'product_code'})
    elif 'GEN_NUM' in df.columns:
        df = df.rename(columns={'GEN_NUM': 'product_code'})
    else:
        raise KeyError("No product code column found (CIP13 or GEN_NUM)")
    df['product_type'] = product_type
    return df

def compare_brand_vs_generic(brand_df: pd.DataFrame, generic_df: pd.DataFrame) -> dict:
    """
    Compare brand vs generic across segments:
    - Region / Age / Gender segments
    - Prescriber type breakdown
    Returns a dict of DataFrames:
      * 'segment_comparison'
      * 'region_summary'
      * 'age_summary'
      * 'gender_summary'
      * 'prescriber_comparison'
    """
    # Load mapping dictionaries
    sex_map, age_map, region_map, presc_map, _ = load_maps()

    brand = prepare_unified(brand_df, 'brand')
    generic = prepare_unified(generic_df, 'generic')

    # Segment-level (region / sex / age)
    brand_seg = brand.groupby(['BEN_REG', 'sexe', 'age'], as_index=False).agg(brand_total=('total_boites', 'sum'))
    generic_seg = generic.groupby(['BEN_REG', 'sexe', 'age'], as_index=False).agg(generic_total=('total_boites', 'sum'))

    seg = pd.merge(brand_seg, generic_seg, on=['BEN_REG', 'sexe', 'age'], how='outer').fillna(0)
    seg['combined_total'] = seg['brand_total'] + seg['generic_total']
    seg['brand_share'] = seg['brand_total'] / seg['combined_total']
    seg = seg.sort_values('brand_share')

    # Map codes to labels in segment comparison
    seg['Region'] = seg['BEN_REG'].astype(str).map(region_map).fillna(seg['BEN_REG'])
    seg['Sex'] = seg['sexe'].astype(str).map(sex_map).fillna(seg['sexe'])
    seg['Age'] = seg['age'].astype(str).map(age_map).fillna(seg['age'])
    seg = seg.drop(columns=['BEN_REG', 'sexe', 'age'])

    # Summaries by one dimension
    region_summary = seg.groupby('Region', as_index=False).agg(
        brand_total=('brand_total', 'sum'),
        generic_total=('generic_total', 'sum')
    )
    region_summary['combined_total'] = region_summary['brand_total'] + region_summary['generic_total']
    region_summary['brand_share'] = region_summary['brand_total'] / region_summary['combined_total']
    region_summary = region_summary.sort_values('brand_share')

    age_summary = seg.groupby('Age', as_index=False).agg(
        brand_total=('brand_total', 'sum'),
        generic_total=('generic_total', 'sum')
    )
    age_summary['combined_total'] = age_summary['brand_total'] + age_summary['generic_total']
    age_summary['brand_share'] = age_summary['brand_total'] / age_summary['combined_total']
    age_summary = age_summary.sort_values('brand_share')

    gender_summary = seg.groupby('Sex', as_index=False).agg(
        brand_total=('brand_total', 'sum'),
        generic_total=('generic_total', 'sum')
    )
    gender_summary['combined_total'] = gender_summary['brand_total'] + gender_summary['generic_total']
    gender_summary['brand_share'] = gender_summary['brand_total'] / gender_summary['combined_total']
    gender_summary = gender_summary.sort_values('brand_share')

    # Prescriber-level breakdown
    prescriber_cols_brand = [c for c in brand.columns if c not in ['BEN_REG', 'sexe', 'age', 'product_code', 'total_boites', 'product_type']]
    prescriber_cols_gen = [c for c in generic.columns if c not in ['BEN_REG', 'sexe', 'age', 'product_code', 'total_boites', 'product_type']]

    brand_presc = brand.melt(
        id_vars=['BEN_REG', 'sexe', 'age'],
        value_vars=prescriber_cols_brand,
        var_name='PSP_SPE',
        value_name='brand_boites'
    )
    generic_presc = generic.melt(
        id_vars=['BEN_REG', 'sexe', 'age'],
        value_vars=prescriber_cols_gen,
        var_name='PSP_SPE',
        value_name='generic_boites'
    )

    presc = pd.merge(
        brand_presc, generic_presc,
        on=['BEN_REG', 'sexe', 'age', 'PSP_SPE'],
        how='outer'
    ).fillna(0)
    presc['combined_total'] = presc['brand_boites'] + presc['generic_boites']
    presc['brand_share'] = presc['brand_boites'] / presc['combined_total']
    presc = presc.sort_values('brand_share')

    # Map codes to labels in prescriber comparison
    presc['Region'] = presc['BEN_REG'].astype(str).map(region_map).fillna(presc['BEN_REG'])
    presc['Sex'] = presc['sexe'].astype(str).map(sex_map).fillna(presc['sexe'])
    presc['Age'] = presc['age'].astype(str).map(age_map).fillna(presc['age'])
    presc['Prescriber'] = presc['PSP_SPE'].astype(str).map(presc_map).fillna(presc['PSP_SPE'])
    presc = presc.drop(columns=['BEN_REG', 'sexe', 'age', 'PSP_SPE'])

    return {
        'segment_comparison': seg,
        'region_summary': region_summary,
        'age_summary': age_summary,
        'gender_summary': gender_summary,
        'prescriber_comparison': presc
    }

def execute_query(cip_list, gen_list):
    # Load environment variables
    DB_SERVER = os.getenv('db-server')
    DB_NAME = os.getenv('db-database')
    DB_USER = os.getenv('db-username')
    DB_PASSWORD = os.getenv('db-password')

    # Instantiate connection
    conn = AzureSQLConnection(
        server=DB_SERVER,
        database=DB_NAME,
        username=DB_USER,
        password=DB_PASSWORD,
        logger=None
    )

    # Load mapping dictionaries
    sex_map, age_map, region_map, presc_map, cpi_map = load_maps()

    # Query for CIP13 (brand)
    query_cip = """
    SELECT 
        BEN_REG,
        sexe,
        age,
        CIP13,
        PSP_SPE,
        BOITES
    FROM dbo.MedicData
    WHERE CIP13 IN ({})
    """.format(','.join(['?'] * len(cip_list)))

    res_json_cip = conn.execute_query(query_cip, cip_list)
    data_cip = json.loads(res_json_cip)
    df_cip = pd.DataFrame(data_cip)
    df_cip['BOITES'] = pd.to_numeric(df_cip['BOITES'], errors='coerce').fillna(0)

    # Total boxes per (region, sex, age, CIP13)
    total_cip = (
        df_cip
        .groupby(['BEN_REG', 'sexe', 'age', 'CIP13'], as_index=False)
        .agg(total_boites=('BOITES', 'sum'))
    )

    # Breakdown by prescriber
    dist_cip = (
        df_cip
        .groupby(['BEN_REG', 'sexe', 'age', 'CIP13', 'PSP_SPE'], as_index=False)
        .agg(boites_by_prescriber=('BOITES', 'sum'))
    )

    # Pivot so each prescriber becomes its own column
    dist_pivot_cip = (
        dist_cip
        .pivot_table(
            index=['BEN_REG', 'sexe', 'age', 'CIP13'],
            columns='PSP_SPE',
            values='boites_by_prescriber',
            fill_value=0
        )
        .reset_index()
    )

    # Merge totals + distribution into one "unified_df"
    unified_df = total_cip.merge(dist_pivot_cip, on=['BEN_REG', 'sexe', 'age', 'CIP13'])

    # Create a copy for mapping categorical variables
    unified_df_mapped = unified_df.copy()

    # Map codes to labels in unified_df_mapped
    unified_df_mapped['Region'] = unified_df_mapped['BEN_REG'].map(lambda x: region_map.get(str(x), str(x)))
    unified_df_mapped['Sex'] = unified_df_mapped['sexe'].map(lambda x: sex_map.get(str(x), str(x)))
    unified_df_mapped['Age'] = unified_df_mapped['age'].map(lambda x: age_map.get(str(x), str(x)))
    unified_df_mapped['Medication'] = unified_df_mapped['CIP13'].map(lambda x: cpi_map.get(str(x), str(x)))

    # Rename prescriber columns
    core_cols = {'BEN_REG', 'sexe', 'age', 'CIP13', 'Region', 'Sex', 'Age', 'Medication', 'total_boites'}
    presc_cols = [c for c in unified_df_mapped.columns if c not in core_cols]
    unified_df_mapped = unified_df_mapped.rename(columns={c: presc_map.get(str(c), str(c)) for c in presc_cols})

    # Drop original numeric columns
    unified_df_mapped = unified_df_mapped.drop(columns=['BEN_REG', 'sexe', 'age', 'CIP13'])

    # Query for GEN_NUM (generic)
    query_gen = """
    SELECT 
        BEN_REG,
        sexe,
        age,
        GEN_NUM,
        PSP_SPE,
        BOITES
    FROM dbo.MedicData
    WHERE GEN_NUM IN ({})
    """.format(','.join(['?'] * len(gen_list)))

    res_json_gen = conn.execute_query(query_gen, gen_list)
    data_gen = json.loads(res_json_gen)
    df_gen = pd.DataFrame(data_gen)
    df_gen['BOITES'] = pd.to_numeric(df_gen['BOITES'], errors='coerce').fillna(0)

    # Total boxes per (region, sex, age, GEN_NUM)
    total_gen = (
        df_gen
        .groupby(['BEN_REG', 'sexe', 'age', 'GEN_NUM'], as_index=False)
        .agg(total_boites=('BOITES', 'sum'))
    )

    # Breakdown by prescriber
    dist_gen = (
        df_gen
        .groupby(['BEN_REG', 'sexe', 'age', 'GEN_NUM', 'PSP_SPE'], as_index=False)
        .agg(boites_by_prescriber=('BOITES', 'sum'))
    )

    # Pivot so each prescriber becomes its own column
    dist_pivot_gen = (
        dist_gen
        .pivot_table(
            index=['BEN_REG', 'sexe', 'age', 'GEN_NUM'],
            columns='PSP_SPE',
            values='boites_by_prescriber',
            fill_value=0
        )
        .reset_index()
    )

    # Merge totals + distribution into one "unified_df_gen"
    unified_df_gen = total_gen.merge(dist_pivot_gen, on=['BEN_REG', 'sexe', 'age', 'GEN_NUM'])

    # Create a copy for mapping categorical variables
    unified_df_gen_mapped = unified_df_gen.copy()

    # Map codes to labels in unified_df_gen_mapped
    unified_df_gen_mapped['Region'] = unified_df_gen_mapped['BEN_REG'].map(lambda x: region_map.get(str(x), str(x)))
    unified_df_gen_mapped['Sex'] = unified_df_gen_mapped['sexe'].map(lambda x: sex_map.get(str(x), str(x)))
    unified_df_gen_mapped['Age'] = unified_df_gen_mapped['age'].map(lambda x: age_map.get(str(x), str(x)))
    unified_df_gen_mapped['Generic'] = unified_df_gen_mapped['GEN_NUM'].astype(str)

    # Rename prescriber columns
    core_cols_gen = {'BEN_REG', 'sexe', 'age', 'GEN_NUM', 'Region', 'Sex', 'Age', 'Generic', 'total_boites'}
    presc_cols_gen = [c for c in unified_df_gen_mapped.columns if c not in core_cols_gen]
    unified_df_gen_mapped = unified_df_gen_mapped.rename(columns={c: presc_map.get(str(c), str(c)) for c in presc_cols_gen})

    # Drop original numeric columns
    unified_df_gen_mapped = unified_df_gen_mapped.drop(columns=['BEN_REG', 'sexe', 'age', 'GEN_NUM'])

    # Compare brand vs generic using the original numeric DataFrames
    metrics = compare_brand_vs_generic(unified_df, unified_df_gen)

    # Convert mapped DataFrames to JSON
    unified_df_json = unified_df_mapped.replace({pd.NA: None, pd.NaT: None, float('nan'): None}).to_dict(orient='records')
    unified_df_gen_json = unified_df_gen_mapped.replace({pd.NA: None, pd.NaT: None, float('nan'): None}).to_dict(orient='records')
    metrics_json = {k: v.replace({pd.NA: None, pd.NaT: None, float('nan'): None}).to_dict(orient='records') for k, v in metrics.items()}

    return {
        'unified_df': unified_df_json,
        'unified_df_gen': unified_df_gen_json,
        'metrics': metrics_json
    }

if __name__ == '__main__':
    # Example usage
    cip_list = ['3400938014792', '3400938014914', '3400938014624']
    gen_list = ['815', '814', '813']
    result = execute_query(cip_list, gen_list)
    print(json.dumps(result, indent=4))
    with open('result.json', 'w') as f:
        json.dump(result, f, indent=4)