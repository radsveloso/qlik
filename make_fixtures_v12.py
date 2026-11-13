#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Synthetic input files for Castine_Python_Replica_v12, in the layout of the real
feeds as the current Qlik script reads them:

  xml      BatchFeed/TradeFeed, Common/*, ExtendedFields/Field[@name],
           TransactionCosts/TransactionCost (Type, Currency, Code, Cost)
  split    RR Teams Split Matrix.xlsx, sheet Split_Matrix
  tiara    tiara.accounts_DDMMYYYY.txt and tiara.subaccounts_DDMMYYYY.txt (pipe)
  repo     <date>/YTDSalesCommission_<date>.csv
  adj      adjustments DailyExportOfPayout_<date>.csv

No real data: every name and number is invented. Each trade exercises one rule
of Castine.py (see the "case" comment of each trade).

Usage: python make_fixtures_v12.py <output folder>
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "tests" / "fixtures_v12"
PAYOUT = "20260130"


def w(path: Path, text: str, encoding="utf-8"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding, newline="\n")


def trade(tx, sec="912797SJ7", ccy="USD", ticker="B", mat="2026-02-03", bs="S",
          td="2026-01-30T10:00:00", asof="2026-01-30T00:00:00", price="99.5", amount="1000000.0",
          acct="3007101391", short="CLIENT A", master="CLIENT A", tname="ED1", tnum="447",
          sales="784", ttype="N", reason="", orig="", costs=(("C", "USD", "C", "1000.00"),),
          sec_typ="US GOVERNMENT", sector="Govt", extra_ext=()):
    common = [
        ("TransactionNumber", tx), ("SecurityIdentifierFlag", "1"), ("SecurityIdentifier", sec),
        ("SecurityCurrencyISOCode", ccy), ("Ticker", ticker), ("MaturityDateExpirationDate", mat),
        ("BuySellCoverShortFlag", bs), ("RecordType", "1"), ("TradeDate", td), ("AsOfTradeDate", asof),
        ("SettlementDate", "2026-02-02T00:00:00"), ("Price", price), ("Yield", "4.1"), ("TradeAmount", amount),
        ("CustomerAccountCounterparty", acct), ("AccountCounterpartyShortName", short),
        ("MasterAccountName", master), ("TraderAccountName", tname), ("TraderAccountNumber", tnum),
        ("SalespersonName", sales), ("TransactionType", ttype), ("OMReasonCode", reason),
        ("SourceCode", "TOMS"), ("OriginalTktId", orig),
    ]
    x = ["  <TradeFeed>", "    <Common>"]
    for k, v in common:
        x.append(f"      <{k}>{escape(v)}</{k}>")
    x.append("    </Common>")
    x.append("    <ExtendedFields>")
    if sec_typ is not None:
        x.append(f'      <Field name="SECURITY_TYP">{escape(sec_typ)}</Field>')
    if sector is not None:
        x.append(f'      <Field name="MARKET_SECTOR_DES">{escape(sector)}</Field>')
    x.append('      <Field name="IGNORED_FIELD">zzz</Field>')
    for n, v in extra_ext:
        x.append(f'      <Field name="{n}">{escape(v)}</Field>')
    x.append("    </ExtendedFields>")
    x.append("    <TransactionCosts>")
    for typ, cur, code, cost in costs:
        x.append("      <TransactionCost>")
        x.append(f"        <Type>{typ}</Type>")
        x.append(f"        <Currency>{cur}</Currency>")
        x.append(f"        <Code>{code}</Code>")
        x.append(f"        <Cost>{cost}</Cost>")
        x.append("        <Rate>0</Rate>")
        x.append("        <CurrencyRate>1</CurrencyRate>")
        x.append("        <Override>N</Override>")
        x.append("      </TransactionCost>")
    x.append("    </TransactionCosts>")
    x.append("    <RepoFields>")
    x.append("      <TransactionType></TransactionType>")
    x.append("    </RepoFields>")
    x.append("  </TradeFeed>")
    return "\n".join(x)


def doc(feeds):
    return '<?xml version="1.0" encoding="UTF-8"?>\n<BatchFeed>\n' + "\n".join(feeds) + "\n</BatchFeed>\n"


def build_xml():
    xml = OUT / "sdrive" / "Trading" / "bloomberg" / "ftp"

    day29 = [
        # case 01: plain trade, one salesperson, one cost
        trade("9000001", sales="784", costs=(("C", "USD", "C", "1000.00"),), td="2026-01-29T10:00:00", asof="2026-01-29T00:00:00"),
        # case 02: first version of a trade amended on the 30th (cost and TradeDate change)
        trade("9000002", sales="784", costs=(("C", "USD", "C", "500.00"),), td="2026-01-29T11:00:00", asof="2026-01-29T00:00:00"),
        # case 03: trade cancelled on the 30th
        trade("9000003", sales="784", costs=(("C", "USD", "C", "300.00"),), td="2026-01-29T12:00:00", asof="2026-01-29T00:00:00"),
        # case 04: as-of in 2025, entered in 2026, ShortDesc GNCL -> cross-year rule removes it
        trade("9000004", sales="784", tname="GNCL", td="2026-01-05T09:00:00", asof="2025-12-31T00:00:00", costs=(("C", "USD", "C", "111.11"),)),
        # case 05: as-of in 2025, entered in 2026, ShortDesc ED1 -> stays
        trade("9000005", sales="784", tname="ED1", td="2026-01-05T09:30:00", asof="2025-12-31T00:00:00", costs=(("C", "USD", "C", "222.22"),)),
        # case 06: team with two salespeople (60 / 40)
        trade("9000006", sales="528", costs=(("C", "USD", "C", "1000.01"),), td="2026-01-29T13:00:00", asof="2026-01-29T00:00:00"),
        # case 07: Add On (Code R) plus primary cost; the Add On comes first in the file
        trade("9000007", sales="784", costs=(("R", "USD", "R", "250.50"), ("C", "USD", "C", "100.00"), ("F", "USD", "F", "9.99")), td="2026-01-29T14:00:00", asof="2026-01-29T00:00:00"),
        # case 08: two Add Ons, no primary cost
        trade("9000008", sales="784", costs=(("R", "USD", "R", "10.005"), ("R", "USD", "r", "20.005")), td="2026-01-29T15:00:00", asof="2026-01-29T00:00:00"),
    ]
    day30_v3 = [
        # this whole file is superseded by version 4 and must not be read
        trade("9999999", sales="784", costs=(("C", "USD", "C", "999999.00"),)),
    ]
    day30 = [
        # case 02b: latest version (cost changed, TradeDate changed) -> Trade Date = As of trade date
        trade("9000002", sales="784", costs=(("C", "USD", "C", "550.00"),), td="2026-01-30T09:00:00", asof="2026-01-30T00:00:00"),
        # case 03b: cancel of 9000003
        trade("9000003", sales="784", ttype="NX", costs=(("C", "USD", "C", "300.00"),), td="2026-01-30T09:10:00", asof="2026-01-30T00:00:00"),
        # case 09: not in USD
        trade("9000009", sales="784", ccy="EUR", costs=(("C", "EUR", "C", "400.00"),)),
        # case 10: currency empty
        trade("9000010", sales="784", ccy="", costs=(("C", "USD", "C", "410.00"),)),
        # case 11: team that is not in the split matrix
        trade("9000011", sales="999", costs=(("C", "USD", "C", "70.00"),)),
        # case 12: no salesperson
        trade("9000012", sales="", costs=(("C", "USD", "C", "80.00"),)),
        # case 13: team whose split version starts on 2026-01-15; trade as of 2026-01-10 -> no active split
        trade("9000013", sales="610", td="2026-01-10T10:00:00", asof="2026-01-10T00:00:00", costs=(("C", "USD", "C", "90.00"),)),
        # case 14: same team, trade as of 2026-01-20 -> active split
        trade("9000014", sales="610", td="2026-01-20T10:00:00", asof="2026-01-20T00:00:00", costs=(("C", "USD", "C", "95.55"),)),
        # case 15: RR Team 235 -> business exclusion
        trade("9000015", sales="235", costs=(("C", "USD", "C", "60.00"),)),
        # case 16: Client TEST -> business exclusion
        trade("9000016", sales="784", master="Test", short="X", costs=(("C", "USD", "C", "61.00"),)),
        # case 17: no MasterAccountName -> Client = AccountCounterpartyShortName; alphanumeric account
        trade("9000017", sales="784", master="", short="SHORT NAME", acct="ABC123", costs=(("C", "USD", "C", "62.00"),)),
        # case 18: numeric account found in tiara.accounts by ACCOUNTNR (leading zeros)
        trade("9000018", sales="784", acct="0000456", costs=(("C", "USD", "C", "63.00"),)),
        # case 19: numeric account found by BLOOMBERG_MASTER_ACCOUNT_NO
        trade("9000019", sales="784", acct="777001", costs=(("C", "USD", "C", "64.00"),)),
        # case 20: numeric account found through tiara.subaccounts
        trade("9000020", sales="784", acct="5550001", costs=(("C", "USD", "C", "65.00"),)),
        # case 21: numeric account in subaccounts whose parent is not in accounts -> alert
        trade("9000021", sales="784", acct="5550002", costs=(("C", "USD", "C", "66.00"),)),
        # case 22: numeric account nowhere -> alert + e-mail table
        trade("9000022", sales="784", acct="88888888", costs=(("C", "USD", "C", "67.00"),)),
        # case 23: numeric account whose ENTITY_CODE is long and numeric -> suspicious
        trade("9000023", sales="784", acct="424242", costs=(("C", "USD", "C", "68.00"),)),
        # case 24: Ticker NA (pandas reads it as empty), cost with thousands separator
        trade("9000024", sales="784", ticker="NA", mat="2030-01-01", costs=(("C", "USD", "C", "1,234.56"),)),
        # case 25: rounding tie in the production (0.125 * 1 -> 0.12 half to even)
        trade("9000025", sales="784", costs=(("C", "USD", "C", "0.125"),)),
        # case 26: negative cost in parentheses, team with lower case and blanks in the split matrix
        trade("9000026", sales="alpha team", costs=(("C", "USD", "C", "(45.50)"),)),
        # case 27: no TransactionNumber, key = OriginalTktId; no cost at all
        trade("", orig="ORIG-77", sales="784", costs=()),
        # case 28: extended fields repeated: the last one wins; empty sector
        trade("9000028", sales="784", sec_typ="FIRST", sector="", extra_ext=(("SECURITY_TYP", "LAST TYPE"),), costs=(("C", "USD", "C", "12.34"),)),
        # case 29: amount with decimals kept as text, zero cost
        trade("9000029", sales="784", amount="46923900.0", costs=(("C", "USD", "C", "0"),)),
        # case 30: commission above 524,288 (the scaled value has no decimals left): 723046.81 * 0.6 and * 0.4
        trade("9000030", sales="528", costs=(("C", "USD", "C", "723046.81"),)),
        # case 31: negative amount that rounds to zero -> the Python writes -0.00
        trade("9000031", sales="528", costs=(("C", "USD", "C", "-0.01"),)),
        # case 32: team whose split rows have N/A and NULL in the date cells
        trade("9000032", sales="840", costs=(("C", "USD", "C", "100.00"),)),
        # case 33: team whose only split row has Salesperson NA -> not mapped
        trade("9000033", sales="850", costs=(("C", "USD", "C", "100.00"),)),
        # case 34: account on a Tiara line with one field too many (left out) and on the line after it
        trade("9000034", sales="784", acct="777555", costs=(("C", "USD", "C", "10.00"),)),
        trade("9000035", sales="784", acct="888777", costs=(("C", "USD", "C", "10.00"),)),
        # case 37: negative cost on a team with a 0% salesperson
        trade("9000039", sales="860", costs=(("C", "USD", "C", "-12.34"),)),
        # case 35: white space that is not a blank at the ends of a value (no-break space, tab)
        trade("9000036", sales="784", master="CLIENT NBSP\u00a0", short="\tSHORT TAB", costs=(("C", "USD", "C", "10.00"),)),
        # case 36: subaccount on a long line (left out) and on the line after it
        trade("9000037", sales="784", acct="5550009", costs=(("C", "USD", "C", "10.00"),)),
        trade("9000038", sales="784", acct="5550010", costs=(("C", "USD", "C", "10.00"),)),
    ]
    w(xml / "f392fd1.ext.260129.4", doc(day29))
    w(xml / "f392fd1.ext.260130.3", doc(day30_v3))
    w(xml / "f392fd1.ext.260130.4", doc(day30))
    # not a versioned name: ignored with a warning
    w(xml / "f392fd1.ext.26x", doc([]))
    # after the date limit of the test (260130): read only without the limit
    w(xml / "f392fd1.ext.260202.4", doc([trade("9100001", sales="784", td="2026-02-02T10:00:00", asof="2026-02-02T00:00:00", costs=(("C", "USD", "C", "5.00"),))]))


def build_split():
    from openpyxl import Workbook
    from datetime import datetime
    wb = Workbook()
    ws0 = wb.active
    ws0.title = "Notes"
    ws0.append(["This sheet has no split columns"])
    ws = wb.create_sheet("Split_Matrix")
    ws.append(["RR Team", "Salesperson", "Split", "Effective Date", "Expiration Date", "Notes", "Version Key", "Version Split Sum", "Version Status"])
    rows = [
        (784, "ANA SILVA", 1, None, None),
        (528, "BRUNO COSTA", 0.6, datetime(2025, 1, 1), None),
        (528, "CARLA DIAS", 0.4, datetime(2025, 1, 1), None),
        (610, "DAVI LIMA", 1, datetime(2026, 1, 15), None),
        (235, "EVA MOTA", 1, None, None),
        ("Alpha  Team", "FABIO NUNES", 50, None, None),          # 50 -> 0.5
        ("ALPHA TEAM", "GINA PIRES", "50%", None, None),          # 50% -> 0.5
        (700, "BAD SUM ONE", 0.7, None, None),                    # version sums 0.9 -> rejected
        (700, "BAD SUM TWO", 0.2, None, None),
        (800, "OVERLAP OLD", 1, datetime(2025, 1, 1), datetime(2026, 6, 30)),   # overlapping windows -> both rejected
        (800, "OVERLAP NEW", 1, datetime(2026, 1, 1), None),
        (None, "NO TEAM", 1, None, None),                         # row checks
        (810, None, 1, None, None),
        (820, "BAD SPLIT", "abc", None, None),
        (830, "BAD ORDER", 1, datetime(2026, 3, 1), datetime(2026, 1, 1)),
        # cells with a pandas NA text: pandas.read_excel reads them as empty cells
        (840, "NA EXPIRY ONE", 0.5, None, "N/A"),                 # N/A -> no expiration date -> valid
        (840, "NA EXPIRY TWO", 0.5, "NULL", None),                # NULL -> no effective date -> valid
        (850, "NA", 1, None, None),                               # Salesperson NA -> empty -> row rejected
        (860, "FULL SHARE", 1, None, None),                       # 100% / 0% version: -x * 0 keeps the sign (-0.00)
        (860, "ZERO SHARE", 0, None, None),
    ]
    for r in rows:
        ws.append(list(r) + ["", "", "", ""])
    p = OUT / "sdrive" / "Qlikview" / "Sales" / "Data" / "Qlik Control Data" / "RR Teams Split Matrix.xlsx"
    p.parent.mkdir(parents=True, exist_ok=True)
    wb.save(p)


def build_tiara():
    folder = OUT / "sdrive" / "Qlikview" / "Sales" / "Data" / "Tiara Accounts"
    acc = [
        "ACCOUNTNR|ACCOUNT_TYPE|ACC_ACTIVE|ENTITY_CODE|BLOOMBERG_MASTER_ACCOUNT_NO|NAME",
        "456|CLIENT|1|GL0456||ACCOUNT 456",
        "0000456|CLIENT|1|GL-SECOND||SAME KEY LATER ROW",
        "9100|CLIENT|1|GL9100|777001|BBG MASTER",
        "31000|CLIENT|1|GL31000||PARENT OF SUBACCOUNT",
        "424242|CLIENT|1|123456789012||LONG NUMERIC ENTITY",
        "55|CLIENT|1|||NO ENTITY CODE",
        # one field more than the header (a | inside the name): pandas leaves the line out
        "777555|CLIENT|1|GLLONG||NAME WITH | PIPE",
        "888777|CLIENT|1|GL888||AFTER THE LONG LINE",
    ]
    sub = [
        "SUBACCT_NO|ACCOUNT_NO|NAME",
        "5550001|31000|SUB ONE",
        "5550002|99999|SUB WITHOUT PARENT",
        "5550001|456|SAME SUBACCOUNT LATER ROW",
        "5550009|31000|SUB WITH | PIPE",
        "5550010|31000|SUB AFTER THE LONG LINE",
    ]
    w(folder / "tiara.accounts_30012026.txt", "\n".join(acc) + "\n", encoding="cp1252")
    w(folder / "tiara.subaccounts_30012026.txt", "\n".join(sub) + "\n", encoding="cp1252")
    # older and newer files that must not be chosen for the payout date 2026-01-30
    w(folder / "tiara.accounts_15012026.txt", "ACCOUNTNR|ENTITY_CODE|BLOOMBERG_MASTER_ACCOUNT_NO\n456|OLD|\n", encoding="cp1252")
    w(folder / "tiara.accounts_15022026.txt", "ACCOUNTNR|ENTITY_CODE|BLOOMBERG_MASTER_ACCOUNT_NO\n456|NEWER|\n", encoding="cp1252")


def build_repo():
    folder = OUT / "sdrive" / "Operations" / "BroadridgeData" / "Reports" / PAYOUT
    rows = [
        "T/D,Account,Cusip,Trans#,SalesPerson,Trader,TR/TYPE,AssetClass,SecurityDescription,Net Credit,Principal",
        "01\\30\\2026,REPO CLIENT A,912828AA1,R0001,784,RPDK,RP,Govt,UST REPO 1,\"1,500.25\",1000000",
        "01\\29\\2026,REPO CLIENT B,912828BB2,R0002,528,RPDK,RR,Govt,UST REPO 2,200.10,2000000.00",
        "1\\2\\2026,REPO CLIENT C,912828CC3,R0003,784,RPDK,RP,Agency,JAN 2 DATE,10.00,300",
        "not a date,REPO CLIENT D,912828DD4,R0004,784,RPDK,RP,Agency,BAD DATE,20.00,400",
        "01\\30\\2026,REPO CLIENT E,912828EE5,R0005,,RPDK,RP,Agency,NO TEAM,30.00,500",
        "01\\30\\2026,REPO CLIENT F,912828FF6,R0006,999,RPDK,RP,Agency,TEAM NOT MAPPED,40.00,600",
        "01\\30\\2026,REPO CLIENT G,912828GG7,R0007,784,RPDK,RP,Agency,NO NET CREDIT,,700",
        "01\\30\\2026,TEST,912828HH8,R0008,784,RPDK,RP,Agency,CLIENT TEST,50.00,800",
        "01\\30\\2026,REPO CLIENT H,912828JJ9,R0009,528,RPDK,RP,Agency,TINY NEGATIVE,-0.01,900",
        "01\\30\\2026,REPO CLIENT J,912828LL1,R0011,860,RPDK,RP,Agency,ZERO SHARE,-250.00,900",
        "01\\30\\2026,REPO CLIENT I,912828KK0,R0010,784,RPDK,RP,Agency,NEGATIVE ZERO,(0.00),900",
    ]
    w(folder / f"YTDSalesCommission_{PAYOUT}.csv", "\n".join(rows) + "\n", encoding="cp1252")


def build_adjustments():
    folder = OUT / "sdrive" / "Qlikview" / "Sales" / "Data"
    header = "As of trade date,Client,Security,Trade Id,Salesperson,Production Earned,Payout Earned,Trader Team Name,Fidelity #,ShortDesc,TradeType,Trade Date,RR Team,Source,Sec Type,Sec Type Description,Security Description,Gross Comms,Acct Short Description,Currency,BuySell,TradeAmount,GLCS CODE"
    rows = [
        header,
        "1/15/2026,ADJ CLIENT,ADJSEC1,ADJ1,ANA SILVA,100.5,100.5,447,,ED1,ADJ,1/15/2026,784,Manual Adjustment,,,MANUAL ROW,100.5,'ADJ001,USD,B,0,GLADJ",
        "1/16/2026,ADJ CLIENT 2,ADJSEC2,ADJ2,ANA SILVA,\"(1,250.75)\",\"(1,250.75)\",447,,ED1,ADJ,1/16/2026,784,Bloomberg XML,,,XML SOURCE ADJ,abc,'0000456,USD,S,10,KEEP",
        "1/17/2026,ADJ CLIENT 3,ADJSEC3,ADJ3,EVA MOTA,5,5,447,,ED1,ADJ,1/17/2026, 235 ,Manual Adjustment,,,TEAM 235,5,'ADJ003,USD,B,0,",
        "1/20/2026,José Pérez Ltda,ADJSEC6,ADJ6,ANA SILVA,1,1,447,,ED1,ADJ,1/20/2026,784,Manual Adjustment,,,AÇÃO,1,'ADJ006,USD,B,0,",
        "1/19/2026,ADJ CLIENT 5,ADJSEC5,ADJ5,ANA SILVA,(0.00),0.005,447,,ED1,ADJ,1/19/2026,784,Manual Adjustment,,,SIGN AND HALF CENT,0.015,'ADJ005,USD,B,0,",
        # values with blanks at both ends: Castine.py keeps them as written (only the money columns are parsed)
        "1/18/2026,  PADDED CLIENT  ,ADJSEC4,ADJ4, ANA SILVA , 7.5 ,7.5,447,,ED1,ADJ,1/18/2026,784,Manual Adjustment,,,  spaced text  ,7.5, 'ADJ004 ,USD,B,0, GL4 ",
    ]
    w(folder / f"adjustments DailyExportOfPayout_{PAYOUT}.csv", "\n".join(rows) + "\n", encoding="utf-8")


def build_config():
    w(OUT / "qlikshare" / "SCRIPT" / "Config_QS.txt",
      "SET SDrive = 'lib://Fldr_SDrive';\nSET SDrive_SalesControlData = 'lib://Fldr_SDrive/Qlikview/Sales/Data/Qlik Control Data';\n")
    (OUT / "sdrive" / "UAT" / "Qlikview" / "Sales" / "Data" / "castine").mkdir(parents=True, exist_ok=True)
    (OUT / "sdrive" / "Qlikview" / "Sales" / "Data" / "castine").mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    build_xml()
    build_split()
    build_tiara()
    build_repo()
    build_adjustments()
    build_config()
    print("fixtures written to", OUT)
