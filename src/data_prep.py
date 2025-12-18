import re 
import pandas as pd

year_fixes = {
    # https://www.lpi.usra.edu/meteor/metbull.php?code=57150 -> the correct year for Northwest Africa 7701 is 2010
    57150: 2010,  
}

stony_iron_re = re.compile(r"(?i)\b(pallasite|mesosiderite)\b")
iron_re = re.compile(r"(?i)\b(iron|hexahedrite|octahedrite|ataxite)\b")
stony_re = re.compile(r"""(?ix)
(
    ^(
        C[IMVORKHBF][0-9./~\-\(\)]*
      | C[0-9][0-9./~\-\(\)]*(?:-ung)?
      | C\b
      | OC[0-9./~\-\(\)]*
      | OC\b
      | H[0-9./~\-\(\)]*
      | L{1,2}[0-9./~\-\(\)]*
      | E[0-9./~\-\(\)]*
      | R[0-9./~\-\(\)]*
      | K[0-9./~\-\(\)]*
      | F[0-9./~\-\(\)]*
    )
  | \b(H|L|LL|E|R|K|F|C|OC)\b
  | chondrite|achondrite|lun|mar
  | acapulcoite|lodra|brachi|winona|breccia|ureil
  | eucrite|diogen|howard|angrite|aubrite
)
""")

def apply_year_fixes(df):
    df = df.copy()
    for meteorID, year in year_fixes.items():
        df.loc[df["id"] == meteorID, "year"] = year
    return df

def exclude_invalid_coordinates(df):
# https://www.lpi.usra.edu/meteor/metbull.php?code=32789 -> id 32789 (Meridiani Planum) found on mars so the location coordinates reported are in Mars
    df = df.copy()
    valid = (
        df["reclat"].between(-90, 90) &
        df["reclong"].between(-180, 180)
    )
    return df[valid]

def add_category(df, col="recclass"):
    s = df[col].fillna("").astype(str)

    m_stony_iron = s.str.contains(stony_iron_re)
    m_iron       = s.str.contains(iron_re)
    m_stony      = s.str.contains(stony_re)

    df = df.copy()
    df["category"] = "Other"
    df.loc[m_stony, "category"] = "Stony"
    df.loc[m_iron, "category"] = "Iron"
    df.loc[m_stony_iron, "category"] = "Stony-iron"  
    return df

def clean_df(df):
    df = df.copy()
    df['id'] = pd.to_numeric(df['id'], errors='coerce')
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["mass (g)"] = pd.to_numeric(df["mass (g)"], errors="coerce")
    df["reclat"] = pd.to_numeric(df["reclat"], errors="coerce")
    df["reclong"] = pd.to_numeric(df["reclong"], errors="coerce")

    df["recclass"] = df["recclass"].fillna("Unclassified")
    df["fall"] = df["fall"].fillna("Unknown")
    df["name"] = df["name"].fillna("Unknown")

    df = df.dropna(subset=["year", "mass (g)", "reclat", "reclong"])
    df = df[df["mass (g)"] > 0]

    df = apply_year_fixes(df)
    df = exclude_invalid_coordinates(df)
    df = add_category(df, col="recclass")

    df["year"] = df["year"].astype(int)
    return df