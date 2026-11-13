#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python emulation of Castine_Python_Replica_v12.qvs, statement by statement.

It is NOT a second copy of Castine.py: every function below follows one LOAD (or
one preceding-load level) of the Qlik script, with the Qlik semantics of the
functions involved (Trim removes blanks only, relational operators compare
numbers when both sides look numeric, Alt returns the first numeric argument,
and so on). Its output is compared with what the original Castine.py writes for
the same input files, so a logic slip in the Qlik script shows up here.

What it cannot show: anything that depends on the Qlik engine itself (syntax,
XmlSimple naming, STORE layout). Those are covered by the help-page checks.

Usage: python sim_v12.py <fixtures folder> [limit token]
       -> writes <fixtures>/sim_v12_payout.csv and prints the comparison with
          <fixtures>/sdrive/Qlikview/Sales/Data/castine/PPT_DailyExportOfPayout_<date>.csv
"""
import csv
import glob
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path

FX = Path(sys.argv[1])
LIMIT = sys.argv[2] if len(sys.argv) > 2 else ""
SD = FX / "sdrive"

EPOCH = date(1899, 12, 30)
PANDAS_FORMAT = 1          # vAsOfPandasFormat of tab 01_Config
OFFICIAL = ["As of trade date", "Client", "Security", "Trade Id", "Salesperson", "Production Earned", "Payout Earned",
            "Trader Team Name", "Fidelity #", "ShortDesc", "TradeType", "Trade Date", "RR Team", "Source", "Sec Type",
            "Sec Type Description", "Security Description", "Gross Comms", "Acct Short Description", "Currency",
            "BuySell", "TradeAmount", "GLCS CODE"]
NA_LIST = {"#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN", "-NaN", "-nan", "1.#IND", "1.#QNAN", "<NA>", "N/A", "NA",
           "NULL", "NaN", "None", "n/a", "nan", "null"}
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"


# ---------------------------------------------------------------- Qlik-like primitives
def trim(s):
    return s.strip(" ")


def ltrim(s):
    return s.lstrip(" ")


def keepchar(s, chars):
    return "".join(c for c in s if c in chars)


def purgechar(s, chars):
    return "".join(c for c in s if c not in chars)


def isdigits(s):
    return len(s) > 0 and len(keepchar(s, DIGITS)) == len(s)


def num_hash(s):
    """Num#(text) with '.' as decimal separator: number or None"""
    if s is None:
        return None
    if re.fullmatch(r"[+-]?(\d+(\.\d*)?|\.\d+)", s):
        return float(s)
    return None


def serial(d):
    return (d - EPOCH).days


def from_serial(n):
    return EPOCH + timedelta(days=int(n))


def fYMD(y, m, d):
    if y is None or m is None or d is None:
        return None
    if not (100 <= y <= 9999 and 1 <= m <= 12 and d >= 1):
        return None
    y, m, d = int(y), int(m), int(d)
    last = (date(y + (m == 12), (m % 12) + 1, 1) - timedelta(days=1)).day
    if d > last:
        return None
    return serial(date(y, m, d))


def fMDY(n):
    if n is None:
        return ""
    d = from_serial(n)
    return f"{d.month}/{d.day}/{d.year}"


def collapse(s):
    for _ in range(5):
        s = s.replace("  ", " ")
    return s


def fTeamKey(s):
    for a, b in ((" ", " "), ("​", ""), ("﻿", ""), ("\t", " "), ("\n", " "), ("\r", " ")):
        s = s.replace(a, b)
    return trim(collapse(s)).upper()


def fCurrencyKey(s):
    for a, b in ((" ", " "), ("​", ""), ("﻿", "")):
        s = s.replace(a, b)
    return purgechar(s.upper(), " \"'\t\n\r")


def fApos(s):
    t = trim(s)
    if len(t) == 0 or t.lower() == "nan":
        return ""
    return t if t[:1] == "'" else "'" + t


def strip_ends(s):
    """fTxt: white space of the Python .strip() that the script removes at both ends"""
    return s.strip(" \t\n\r\u00a0")


def fXml(v):
    if v is None:
        return ""
    t = strip_ends(v)
    return "" if t in NA_LIST else t


def fNa(v):
    if v is None:
        return ""
    return "" if v in NA_LIST else v


def rint_half_even(y):
    """fRound2 / fRound10: part above a half, part below a half, exact half to the even number"""
    f = math.floor(y)
    if y - f > 0.5:
        return f + 1
    if y - f < 0.5:
        return f
    return f if math.floor(f / 2) * 2 == f else f + 1


def fRound2(x):
    if x is None:
        return None
    return rint_half_even(x * 100) / 100


def fFmt2(x):
    """Tab 13_Export: cent nearest to the exact value, an exact half goes to the even cent (Python "%.2f")"""
    if x is None:
        return None
    y = x * 100
    f = math.floor(y)
    frac = y - f
    hi = 134217729 * x - (134217729 * x - x)
    err = (hi * 100 - y) + (x - hi) * 100
    if frac > 0.5:
        n = f + 1
    elif frac < 0.5:
        n = f
    elif err > 0:
        n = f + 1
    elif err < 0:
        n = f
    else:
        n = f if f % 2 == 0 else f + 1
    return n / 100


def digit_mask(s):
    for d in "012345678":
        s = s.replace(d, "9")
    return s


def column_date_shape(first):
    """SUB ColumnDateShape: (strict, shape) of a date column from its first non-empty value"""
    if len(first) > 0:
        y, m, d = num_hash(first[0:4]), num_hash(first[5:7]), num_hash(first[8:10])
        if fIsIso(first) and "'" not in first and ";" not in first and fYMD(y, m, d) is not None:
            return (PANDAS_FORMAT == 1), digit_mask(first)
    return False, "@none"


def fRound10(x):
    if x is None:
        return None
    return rint_half_even(x * 10000000000) / 10000000000


def fIsIso(s):
    return (s[4:5] == "-" and s[7:8] == "-" and len(keepchar(s[:10], DIGITS)) == 8
            and (len(s) == 10 or s[10:11] in ("T", " ")))


def strip_char(s, q):
    """Replace(Replace(Trim(Replace(Replace(s,' ',Chr(1)),q,' ')),' ',q),Chr(1),' ')"""
    return trim(s.replace(" ", "\x01").replace(q, " ")).replace(" ", q).replace("\x01", " ")


# ---------------------------------------------------------------- SUB BuildDateMap
def build_date(raw):
    t0 = trim(raw.replace(" ", " ").replace("​", "").replace("�", ""))
    t1 = strip_char(t0, '"')
    t2 = strip_char(t1, "'")
    t3 = t2.replace("\\", "/").replace("\t", " ").replace("\n", " ").replace("\r", " ")
    blank = len(t2) == 0 or t2.lower() in ("nan", "nat", "none", "null")
    s = trim(collapse(t3))
    digits = keepchar(s, DIGITS)
    nd = len(digits)
    neg = s[:1] == "-"
    body = s[1:] if s[:1] in ("+", "-") else s
    sp0 = s.replace(" ", "\x01").replace("-", " ").replace(".", " ").replace("/", " ")
    qs0 = s[:s.index(" ")].replace("-", " ").replace(".", " ").replace("/", " ") if (" " in s and ":" in s) else ""
    sp = trim(collapse(sp0))
    qs = trim(collapse(qs0))

    def parts(x):
        return x.split(" ") if len(x) > 0 else []

    ip = body[:body.index(".")] if "." in body else body
    fp = body[body.index(".") + 1:] if "." in body else ""
    hasdot = "." in body
    pp = parts(sp)
    np_ = len(pp)
    p1, p2, p3 = (pp + [None, None, None])[:3]
    a = num_hash(digits[0:2]); b = num_hash(digits[2:4]); c6 = num_hash(digits[4:6]); c8 = num_hash(digits[4:8])
    y8 = num_hash(digits[0:4]); m8 = num_hash(digits[4:6]); d8 = num_hash(digits[6:8])
    isoshape = (len(s) > 10 and s[4:5] == "-" and s[7:8] == "-" and s[10:11] in ("T", " ")
                and len(keepchar(s[:10], DIGITS)) == 8)
    i1 = num_hash(s[0:4]); i2 = num_hash(s[5:7]); i3 = num_hash(s[8:10])
    qq = parts(qs)
    qnp = len(qq)
    q1, q2, q3 = (qq + [None, None, None])[:3]

    def is14(x):
        return x is not None and 1 <= len(x) <= 4 and isdigits(x)

    isint = len(ip) > 0 and isdigits(ip) and ((not hasdot) or (len(fp) > 0 and len(purgechar(fp, "0")) == 0))
    ipz = ltrim(ip.replace("0", " ")).replace(" ", "0")
    yy6 = None if c6 is None else (2000 + c6 if c6 <= 79 else 1900 + c6)
    yy6b = None if a is None else (2000 + a if a <= 79 else 1900 + a)
    pok = np_ == 3 and is14(p1) and is14(p2) and is14(p3)
    n1 = num_hash(p1) if p1 is not None else None
    n2 = num_hash(p2) if p2 is not None else None
    n3 = num_hash(p3) if p3 is not None else None
    py2 = None if n3 is None else (2000 + n3 if n3 <= 79 else 1900 + n3)
    qok = qnp == 3 and is14(q1) and is14(q2) and q3 is not None and len(q3) == 4 and is14(q3)
    qn1 = num_hash(q1) if q1 is not None else None
    qn2 = num_hash(q2) if q2 is not None else None
    qn3 = num_hash(q3) if q3 is not None else None

    dserial = None
    if isint and not neg and 1 <= len(ipz) <= 7:
        v = num_hash(ipz)
        if v is not None and v <= 2958465:
            dserial = v
    d8ymd = fYMD(y8, m8, d8) if (nd == 8 and digits[:2] in ("19", "20")) else None
    d8mdy = fYMD(c8, a, b) if nd == 8 else None
    d8dmy = fYMD(c8, b, a) if nd == 8 else None
    d6mdy = fYMD(yy6, a, b) if nd == 6 else None
    d6dmy = fYMD(yy6, b, a) if nd == 6 else None
    d6ymd = fYMD(yy6b, b, c6) if nd == 6 else None
    p_ymd = fYMD(n1, n2, n3) if (pok and len(p1) == 4) else None
    p_mdy4 = fYMD(n3, n1, n2) if (pok and len(p3) == 4) else None
    p_dmy4 = fYMD(n3, n2, n1) if (pok and len(p3) == 4) else None
    p_mdy2 = fYMD(py2, n1, n2) if (pok and len(p3) == 2) else None
    p_dmy2 = fYMD(py2, n2, n1) if (pok and len(p3) == 2) else None
    diso = fYMD(i1, i2, i3) if isoshape else None
    q_mdy = fYMD(qn3, qn1, qn2) if qok else None
    q_dmy = fYMD(qn3, qn2, qn1) if qok else None

    def alt(*xs):
        for x in xs:
            if x is not None:
                return x
        return None

    def gt(x, y):
        return x is not None and x > y

    def le(x, y):
        return x is not None and x <= y

    def pick(x, y, mdy, dmy, *more):
        if gt(x, 12) and le(y, 12) and dmy is not None:
            return dmy
        if gt(y, 12) and le(x, 12) and mdy is not None:
            return mdy
        return alt(mdy, dmy, *more)

    pick8 = pick(a, b, d8mdy, d8dmy)
    pick6 = pick(a, b, d6mdy, d6dmy, d6ymd)
    p4pick = pick(n1, n2, p_mdy4, p_dmy4)
    p2pick = pick(n1, n2, p_mdy2, p_dmy2)
    compact = alt(d8ymd, pick8) if nd == 8 else (pick6 if nd == 6 else None)
    partsd = alt(p_ymd, p4pick, p2pick) if pok else None
    usdt = alt(q_mdy, q_dmy) if qok else None
    if blank:
        return None
    r = alt(dserial, compact, partsd, diso, usdt)
    return None if r is None else int(r)


# ---------------------------------------------------------------- SUB BuildNumMap
def build_num(raw):
    blank = len(trim(raw)) == 0 or trim(raw).lower() == "nan"
    k = keepchar(raw, "0123456789.,-+()")
    paren = "(" in k and ")" in k
    a = purgechar(k, "()") if paren else k
    b = a[1:] if a[:1] == "+" else a
    neg = paren or b[:1] == "-"
    c = purgechar(b[1:] if b[:1] == "-" else b, "+-")
    hasdot = "." in c
    hascomma = "," in c
    ci = c[:c.index(",")] if "," in c else c
    cf = c[c.index(",") + 1:] if "," in c else ""
    if hasdot and hascomma:
        d = purgechar(c, ",") if c.rindex(".") > c.rindex(",") else purgechar(c, ".").replace(",", ".")
    elif hascomma:
        if c.count(",") > 1:
            d = purgechar(c, ",")
        elif len(cf) in (1, 2):
            d = ci + "." + cf
        elif len(cf) == 3 and len(ci) <= 3:
            d = ci + "." + cf
        else:
            d = ci + cf
    elif hasdot and c.count(".") > 1:
        d = purgechar(c[:c.rindex(".")], ".") + "." + c[c.rindex(".") + 1:]
    else:
        d = c
    dig = keepchar(d, DIGITS)
    e = "0" + d if d[:1] == "." else d
    ok = len(dig) > 0 and d.count(".") <= 1 and len(d) - len(dig) == d.count(".")
    f = e[:-1] if e[-1:] == "." else e
    if blank or not ok:
        return None
    v = num_hash(f)
    if neg:
        return -0.000000000001 if v == 0 else -abs(v)
    return v


# ---------------------------------------------------------------- SUB BuildAcctMaps
def acct_keys(raw):
    t0 = trim(raw.replace(" ", " ").replace("​", "").replace("﻿", ""))
    t1 = strip_char(t0, '"')
    t3 = trim(strip_char(t1, "'"))
    blank = len(t3) == 0 or t3.lower() in ("nan", "none", "null", "nat")
    alpha = len(keepchar(t3, LETTERS)) > 0
    ipart = t3[:t3.index(".")] if "." in t3 else ""
    dot = t3.find(".") + 1                                   # Index(): 1-based, 0 when not found
    dotzero = (dot > 1 and len(keepchar(t3[:dot - 1], DIGITS)) == dot - 1 and len(t3) > dot
               and len(purgechar(t3[dot:], "0")) == 0)
    clean = "" if blank else t3
    base = "" if (blank or alpha) else (ipart if dotzero else keepchar(t3, DIGITS))
    if len(base) == 0:
        nz = ""
    else:
        z = ltrim(base.replace("0", " ")).replace(" ", "0")
        nz = "0" if len(z) == 0 else z
    return base, nz, clean


# ---------------------------------------------------------------- 03_XML_Files
def tok_date(tok):
    def n(x):
        return num_hash(x) if x != "" else None
    tok6 = tok[2:] if (len(tok) == 8 and tok[:2] == "26") else (tok if len(tok) == 6 else "")
    if len(tok) == 8 and tok[:2] == "20":
        return fYMD(n(tok[0:4]), n(tok[4:6]), n(tok[6:8]))
    if len(tok6) == 6:
        y = n(tok6[0:2])
        return fYMD(None if y is None else 2000 + y, n(tok6[2:4]), n(tok6[4:6]))
    return None


def is_tok(x):
    return x is not None and 6 <= len(x) <= 8 and isdigits(x)


def xml_files():
    paths = sorted(glob.glob(str(SD / "Trading" / "bloomberg" / "ftp" / "*.ext.26*")))
    rows = []
    for p in paths:
        name = os.path.basename(p)
        segs = name.split(".")
        ver = segs[-1]
        ver_ok = name.count(".") >= 3 and len(ver) > 0 and isdigits(ver)
        m2 = segs[-2] if name.count(".") >= 1 else ""
        if ver_ok and is_tok(m2):
            token = m2
        else:
            token = next((x for x in segs[:6] if is_tok(x)), "")
        rows.append({"path": p, "name": name, "ver_ok": ver_ok,
                     "key": p[:len(p) - len(ver) - 1].lower() if ver_ok else "",
                     "ver": float(ver) if ver_ok else None, "token": token, "date": tok_date(token)})
    valid = [r for r in rows if r["ver_ok"]]
    best = {}
    for r in valid:
        best[r["key"]] = max(best.get(r["key"], -1), r["ver"])
    pick = {}
    for r in valid:
        if r["ver"] == best[r["key"]]:
            pick[r["key"]] = max(pick.get(r["key"], ""), r["path"])
    sel = [r for r in valid if pick.get(r["key"]) == r["path"]]
    lim = tok_date_limit(LIMIT)
    sel = [r for r in sel if lim < 0 or r["date"] is None or r["date"] <= lim]
    sel.sort(key=lambda r: r["path"])
    dates = [r["date"] for r in sel if r["date"] is not None]
    if dates:
        payout = max(dates)
    else:
        payout = serial(date.today()) - 1
        wd = (payout + 5) % 7
        payout -= 1 if wd == 5 else (2 if wd == 6 else 0)
    return sel, payout


def tok_date_limit(tok):
    t = keepchar(tok, DIGITS)
    d = tok_date(t)
    return -1 if d is None else d


# ---------------------------------------------------------------- 04_Split_Matrix
def cell_text(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (datetime, date)):
        d = v.date() if isinstance(v, datetime) else v
        return f"{d.month}/{d.day}/{d.year}"
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def cell_num(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (datetime, date)):
        dt = v if isinstance(v, datetime) else datetime(v.year, v.month, v.day)
        return (dt - datetime(1899, 12, 30)).total_seconds() / 86400
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        t = v.strip()
        if t.endswith("%"):
            n = num_hash(t[:-1])
            return None if n is None else n / 100          # Qlik reads '50%' as the number 0.5
        return num_hash(t)
    return None


def split_value(split_cellnum, split_text):
    """Split of one row of the matrix as the script computes it (number of the cell first, text second)"""
    pct = "%" in split_text
    t2 = keepchar(split_text.replace(",", "."), "0123456789.-")
    t3 = t2[1:] if t2[:1] == "-" else t2
    tok = len(keepchar(t3, DIGITS)) > 0 and "-" not in t3 and t3.count(".") <= 1
    t4 = ("0" if t3[:1] == "." else "") + (t3[:-1] if t3[-1:] == "." else t3)
    tval = (-1 if t2[:1] == "-" else 1) * num_hash(t4) if tok else None
    if split_cellnum is not None:
        v1 = split_cellnum / 100 if split_cellnum > 1 else split_cellnum
    elif tok:
        v1 = tval / 100 if (pct or tval > 1) else tval
    else:
        v1 = None
    return None if (v1 is None or v1 < 0 or v1 > 1) else v1


def split_matrix():
    from openpyxl import load_workbook
    TS_MIN, TS_MAX = serial(date(1900, 1, 1)), serial(date(2262, 4, 11))
    wb = load_workbook(SD / "Qlikview" / "Sales" / "Data" / "Qlik Control Data" / "RR Teams Split Matrix.xlsx", data_only=True)
    ws = wb["Split_Matrix"]
    it = ws.iter_rows(values_only=True)
    hdr = [str(h) if h is not None else "" for h in next(it)]
    col = {h: i for i, h in enumerate(hdr)}
    rows = []
    for rn, r in enumerate(it, 1):
        if all(v is None for v in r):
            continue
        rr_raw = fNa(cell_text(r[col["RR Team"]]))
        sp = strip_ends(fNa(cell_text(r[col["Salesperson"]])))
        split_text = trim(fNa(cell_text(r[col["Split"]])))
        split_cellnum = cell_num(r[col["Split"]])
        eff_text = trim(fNa(cell_text(r[col["Effective Date"]]))); eff_num = cell_num(r[col["Effective Date"]])
        exp_text = trim(fNa(cell_text(r[col["Expiration Date"]]))); exp_num = cell_num(r[col["Expiration Date"]])
        rr_norm = fTeamKey(rr_raw)
        split_num = split_value(split_cellnum, split_text)

        def dt(num, text):
            if num is not None and 0 < num <= 2958465:
                return math.floor(num)
            return build_date(text)
        eff_date = dt(eff_num, eff_text); exp_date = dt(exp_num, exp_text)
        eff_cmp = eff_date if eff_date is not None else TS_MIN
        exp_cmp = exp_date if exp_date is not None else TS_MAX
        vk = rr_norm + "||" + from_serial(eff_cmp).strftime("%Y%m%d") + "||" + from_serial(exp_cmp).strftime("%Y%m%d")
        bad = (len(rr_norm) == 0 or len(sp) == 0 or split_num is None or (len(eff_text) > 0 and eff_date is None)
               or (len(exp_text) > 0 and exp_date is None)
               or (eff_date is not None and exp_date is not None and eff_date > exp_date))
        rows.append({"row": rn, "rr_raw": rr_raw, "rr_norm": rr_norm, "rr_key": "T|" + rr_norm, "sp": sp,
                     "split_num": split_num, "eff": eff_cmp, "exp": exp_cmp, "vk": vk, "ok": not bad})
    sums = {}
    for r in rows:
        if r["ok"]:
            sums[r["vk"]] = sums.get(r["vk"], 0) + r["split_num"]
    wins = {(r["rr_key"], r["vk"], r["eff"], r["exp"]) for r in rows if r["ok"]}
    over = set()
    for (t1, k1, e1, x1) in wins:
        for (t2, k2, e2, x2) in wins:
            if t1 == t2 and k1 != k2 and e1 <= x2 and e2 <= x1:
                over.add(k1)
    valid = [r for r in rows if r["ok"] and not (abs(sums.get(r["vk"], 0) - 1) > 0.001) and r["vk"] not in over]
    valid.sort(key=lambda r: r["row"])
    return valid


# ---------------------------------------------------------------- 05_Tiara
def header_norm(h):
    return keepchar(h.replace(" ", " ").lower(), "abcdefghijklmnopqrstuvwxyz0123456789")


def pick_charset(path, fallback="cp1252"):
    """SUB PickCharSet: utf-8 when the bytes 128-255 of the file form valid UTF-8 sequences by count"""
    b = open(path, "rb").read()
    cont = sum(1 for c in b if 0x80 <= c <= 0xBF)
    need = sum(1 for c in b if 0xC2 <= c <= 0xDF) + 2 * sum(1 for c in b if 0xE0 <= c <= 0xEF) + 3 * sum(1 for c in b if 0xF0 <= c <= 0xF4)
    bad = sum(1 for c in b if c in (0xC0, 0xC1) or c >= 0xF5)
    return "utf-8" if (bad == 0 and need > 0 and cont == need) else fallback


def read_lines(path, delim, encoding):
    """Tiara files: read line by line; a line with more fields than the header is left out"""
    with open(path, encoding=encoding, newline="") as f:
        lines = f.read().split("\n")
    lines = [l.rstrip("\r") for l in lines]
    hdr = [h.strip(" ") for h in lines[0].split(delim)]
    out = []
    for l in lines[1:]:
        parts = l.split(delim)
        if len(parts) > len(hdr):
            continue
        out.append({hdr[i]: (parts[i] if i < len(parts) else None) for i in range(len(hdr))})
    return hdr, out


def read_delimited(path, delim, quoted, encoding):
    with open(path, encoding=encoding, newline="") as f:
        if quoted:
            rd = csv.reader(f, delimiter=delim)
        else:
            rd = csv.reader(f, delimiter=delim, quoting=csv.QUOTE_NONE)
        rows = [r for r in rd if r]
    hdr = rows[0]
    out = []
    for r in rows[1:]:
        out.append({hdr[i]: (r[i] if i < len(r) else None) for i in range(len(hdr))})
    return hdr, out


def pick_col(hdr, targets):
    norms = [(h, header_norm(h)) for h in hdr]
    for t in targets.split("|"):
        for h, n in norms:
            if n == t:
                return h
    return None


def col_text(row, colname):
    if colname is None:
        return ""
    v = row.get(colname)
    return "" if v is None else strip_ends(v)


def pick_tiara(family, payout):
    folder = SD / "Qlikview" / "Sales" / "Data" / "Tiara Accounts"
    files = sorted(glob.glob(str(folder / f"tiara.{family}*")))
    if not files:
        return None
    dmy = from_serial(payout).strftime("%d%m%Y")
    cand = []
    for p in files:
        name = os.path.basename(p)
        rest = name.lower()[len("tiara." + family):]
        exact = dmy in rest
        tok = ltrim(rest.replace("_", " ").replace("-", " ").replace(".", " "))[:8]
        d = fYMD(num_hash(tok[4:8]), num_hash(tok[2:4]), num_hash(tok[0:2])) if (len(tok) == 8 and isdigits(tok)) else None
        grp = 1 if exact else (2 if (d is not None and d <= payout) else 3)
        cand.append((grp, d, p))
    g = min(c[0] for c in cand)
    if g == 2:
        bd = max(c[1] for c in cand if c[0] == 2)
        cs = [c[2] for c in cand if c[0] == 2 and c[1] == bd]
    else:
        cs = [c[2] for c in cand if c[0] == g]
    cs.sort()
    if len(cs) == 1:
        return cs[0]
    best, bt = None, -1
    for p in cs:
        t = os.path.getmtime(p)
        if t >= bt:
            best, bt = p, t
    return best


def tiara_maps(payout):
    direct, accnr, sub = {}, {}, {}
    accf = pick_tiara("accounts", payout)
    if accf:
        hdr, rows = read_lines(accf, "|", pick_charset(accf))
        ce, ca, cb = pick_col(hdr, "entitycode"), pick_col(hdr, "accountnr|accountno"), pick_col(hdr, "bloombergmasteraccountno|masterbloombergaccount")
        if ce is not None and not (ca is None and cb is None):
            keys = []
            for i, r in enumerate(rows, 1):
                ent = col_text(r, ce)
                if len(ent) == 0:
                    continue
                ab, anz, _ = acct_keys(col_text(r, ca))
                bb, bnz, _ = acct_keys(col_text(r, cb))
                keys += [(ab, ent, i * 4 + 1, 1), (anz, ent, i * 4 + 2, 1), (bb, ent, i * 4 + 3, 0), (bnz, ent, i * 4 + 4, 0)]
            for k, ent, seq, isacc in sorted(keys, key=lambda x: x[2]):
                if len(k) == 0:
                    continue
                direct.setdefault(k, ent)
                if isacc:
                    accnr.setdefault(k, ent)
    subf = pick_tiara("subaccounts", payout)
    if subf:
        hdr, rows = read_lines(subf, "|", pick_charset(subf))
        ca, cs = pick_col(hdr, "accountno|accountnr"), pick_col(hdr, "subacctno|subaccountno|subaccountnr")
        if ca is not None and cs is not None:
            keys = []
            for i, r in enumerate(rows, 1):
                acc = col_text(r, ca); sb = col_text(r, cs)
                ab, anz, _ = acct_keys(acc)
                if len(ab) == 0:
                    continue
                sbase, snz, _ = acct_keys(sb)
                keys += [(sbase, sb, acc, ab, anz, i * 2 + 1), (snz, sb, acc, ab, anz, i * 2 + 2)]
            for k, sb, acc, ab, anz, seq in sorted(keys, key=lambda x: x[5]):
                if len(k) == 0:
                    continue
                sub.setdefault(k, (sb, acc, ab, anz))
    return direct, accnr, sub


# ---------------------------------------------------------------- file choice (PickRankedFile)
def pick_ranked(pattern, prefixes, exts, undated, ymd):
    files = sorted(glob.glob(pattern))
    best = {}
    for p in files:
        if not os.path.isfile(p):
            continue
        name = os.path.basename(p)
        lname = name.lower()
        dig = keepchar(name, DIGITS)
        suffix = "." + name.split(".")[-1].lower() if name.find(".") + 1 > 1 else "@"
        if suffix not in exts.split("|"):
            continue
        rank = 999999
        for pi, pref in enumerate(prefixes.split("|"), 1):
            pref = pref.lower()
            for ei, ext in enumerate(exts.split("|"), 1):
                ext = "" if ext == "@" else ext.lower()
                if lname == pref + ymd + ext:
                    r = (pi - 1) * 10 + ei
                elif undated and lname == pref + ext:
                    r = 500 + (pi - 1) * 10 + ei
                elif lname[:len(pref)] == pref and ymd in dig:
                    r = 1000
                elif lname[:len(pref)] == pref:
                    r = 2000
                else:
                    r = 999999
                rank = min(rank, r)
        best[p] = rank
    if not best:
        return None
    m = min(best.values())
    if m >= 999999:
        return None
    cs = sorted(p for p, r in best.items() if r == m)
    if len(cs) == 1:
        return cs[0]
    out, bt = None, -1
    for p in cs:
        t = os.path.getmtime(p)
        if t >= bt:
            out, bt = p, t
    return out


# ---------------------------------------------------------------- 08_XML_Read (what XmlSimple delivers)
def local(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag


def read_xml(sel):
    trades = []
    for fno, f in enumerate(sel, 1):
        try:
            root = ET.parse(f["path"]).getroot()
        except Exception:
            continue
        if local(root.tag) != "BatchFeed":
            continue
        feed_no = 0
        for tf in root:
            if local(tf.tag) != "TradeFeed":
                continue
            feed_no += 1
            common = {}
            for ch in tf:
                if local(ch.tag) == "Common":
                    for c in ch:
                        common[local(c.tag)] = c.text
            costs = []
            for ch in tf:
                if local(ch.tag) == "TransactionCosts":
                    for tc in ch:
                        if local(tc.tag) == "TransactionCost":
                            d = {local(x.tag): x.text for x in tc}
                            costs.append((fXt(d.get("Code")), fXt(d.get("Cost"))))
            ext = []
            for ch in tf:
                if local(ch.tag) == "ExtendedFields":
                    for fl in ch:
                        if local(fl.tag) == "Field" and fl.get("name") in ("SECURITY_TYP", "MARKET_SECTOR_DES"):
                            ext.append((fl.get("name"), fXt(fl.text)))
            g = lambda k: fXml(common.get(k))
            row = {k: g(k) for k in ["TransactionNumber", "OriginalTktId", "SecurityIdentifier", "SecurityCurrencyISOCode", "Ticker",
                                      "MaturityDateExpirationDate", "BuySellCoverShortFlag", "TradeDate", "AsOfTradeDate", "Price",
                                      "TradeAmount", "CustomerAccountCounterparty", "AccountCounterpartyShortName", "MasterAccountName",
                                      "TraderAccountName", "TraderAccountNumber", "SalespersonName", "TransactionType", "OMReasonCode"]}
            prim = [c for code, c in costs if len(c) > 0 and code.upper() != "R"]
            addon = [build_num(c) for code, c in costs if len(c) > 0 and code.upper() == "R"]
            addon_n = [x for x in addon if x is not None]
            st = [v for n, v in ext if n == "SECURITY_TYP"]
            ms = [v for n, v in ext if n == "MARKET_SECTOR_DES"]
            row.update({"file_no": fno, "feed_no": feed_no, "source_file": f["name"], "file_date_token": f["token"],
                        "SECURITY_TYP": fNa(st[-1] if st else None), "MARKET_SECTOR_DES": fNa(ms[-1] if ms else None),
                        "Cost_original": fNa(prim[0] if prim else None),
                        "AddOn_original": fmt10(fRound10(sum(addon_n))) if len(addon_n) > 0 else ""})
            trades.append(row)
    return trades


def fXt(v):
    return "" if v is None else strip_ends(v)


def fmt10(x):
    s = f"{x:.10f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


# ---------------------------------------------------------------- 09_XML_Versions
def xml_date(s):
    if fIsIso(s):
        return fYMD(num_hash(s[0:4]), num_hash(s[5:7]), num_hash(s[8:10]))
    return build_date(s)


def versions(trades):
    # version order as pandas: the format of the first non-empty AsOfTradeDate is the format of the column
    firsts = [t for t in sorted(trades, key=lambda t: t["file_no"] * 100000000 + t["feed_no"])
              if len(t["AsOfTradeDate"]) > 0 and t["AsOfTradeDate"] not in ("NaT", "nat", "NAT", "NAN")]
    first = firsts[0]["AsOfTradeDate"] if firsts else ""
    strict, shape = column_date_shape(first)
    for t in trades:
        t["grp_key"] = "~" + (t["TransactionNumber"] if len(t["TransactionNumber"]) > 0 else
                              (t["OriginalTktId"] if len(t["OriginalTktId"]) > 0 else
                               t["SecurityIdentifier"] + "||" + t["TradeDate"] + "||" + t["TradeAmount"]))
        tn = num_hash(t["file_date_token"])
        t["token_order"] = tn if tn is not None else 0
        t["read_order"] = t["file_no"] * 100000000 + t["feed_no"]
        a = t["AsOfTradeDate"]
        t["asof_date"] = xml_date(a) if len(a) > 0 else None
        tm = 0
        if fIsIso(a):
            m = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})", a[11:19])
            if m and int(m.group(1)) < 24 and int(m.group(2)) < 60 and int(m.group(3)) < 60:
                tm = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))) / 86400
        other_format = strict and digit_mask(a) != shape
        t["asof_order"] = -999999999 if (t["asof_date"] is None or other_format) else t["asof_date"] + tm
    ids = {}
    for t in trades:
        t["grp_id"] = ids.setdefault(t["grp_key"], len(ids) + 1)
    trades.sort(key=lambda t: (t["grp_id"], t["token_order"], t["asof_order"], t["read_order"]))
    prev = None
    for t in trades:
        own = "" if t["TradeDate"].lower() in ("nan", "nat", "none", "null") else t["TradeDate"]
        if prev is not None and prev["grp_id"] == t["grp_id"]:
            t["version_no"] = prev["version_no"] + 1
            t["first_trade_date"] = prev["first_trade_date"] if len(prev["first_trade_date"]) > 0 else own
        else:
            t["version_no"] = 1
            t["first_trade_date"] = own
        prev = t
    latest = {}
    for t in trades:
        latest[t["grp_id"]] = t
    out = [t for t in latest.values() if "x" not in t["TransactionType"].lower()]
    n_versioned = len(latest)
    for t in out:
        t["trade_date_text"] = t["first_trade_date"] if len(t["first_trade_date"]) > 0 else t["TradeDate"]
        t["trade_date_out"] = xml_date(t["trade_date_text"]) if len(t["trade_date_text"]) > 0 else None
        t["trade_date_row"] = xml_date(t["TradeDate"]) if len(t["TradeDate"]) > 0 else None
    return out, n_versioned


# ---------------------------------------------------------------- 10..13
def apply_split(rows, split, key, date_field):
    out = []
    for r in rows:
        if len(r[key]) == 0:
            continue
        rk = "T|" + fTeamKey(r[key])
        for s in split:
            if s["rr_key"] == rk and s["eff"] <= r[date_field] <= s["exp"]:
                out.append((r, s))
    return out


def money(x):
    if x is None:
        return ""
    r = fFmt2(x)
    if x < 0 and r == 0:
        return "-0.00"
    return f"{r:.2f}"


def main():
    sel, payout = xml_files()
    ymd = from_serial(payout).strftime("%Y%m%d")
    split = split_matrix()
    direct, accnr, sub = tiara_maps(payout)
    trades = read_xml(sel)
    active, n_versioned = versions(trades)
    active.sort(key=lambda t: t["grp_key"])
    core = []
    # split date as pandas reads the two columns: format of the first non-empty value, trades in key order
    def first_shape(field):
        vals = [t[field] for t in active if len(t[field]) > 0 and t[field] not in ("NaT", "nat", "NAT", "NAN")]
        first = vals[0] if vals else ""
        return column_date_shape(first)
    strict_a, shape_a = first_shape("AsOfTradeDate")
    strict_t, shape_t = first_shape("TradeDate")
    for t in active:
        sa = None if (strict_a and digit_mask(t["AsOfTradeDate"]) != shape_a) else t["asof_date"]
        st = None if (strict_t and digit_mask(t["TradeDate"]) != shape_t) else t["trade_date_row"]
        t["split_date"] = sa if sa is not None else (st if st is not None else payout)
    matched = apply_split(active, split, "SalespersonName", "split_date")
    for t, s in matched:
        cost = build_num(t["Cost_original"]); addon = build_num(t["AddOn_original"])
        total = fRound10((cost or 0) + (addon or 0))
        prod_raw = total * s["split_num"]
        prod = -0.000001 if (total < 0 and fRound2(prod_raw) == 0) else fRound2(prod_raw)
        gross = -0.000001 if (total < 0 and fRound2(total) == 0) else fRound2(total)
        if fCurrencyKey(t["SecurityCurrencyISOCode"]) != "USD":
            continue
        core.append({"As of trade date": fMDY(t["asof_date"]),
                     "Client": t["MasterAccountName"] if len(t["MasterAccountName"]) > 0 else t["AccountCounterpartyShortName"],
                     "Security": t["SecurityIdentifier"], "Trade Id": t["TransactionNumber"], "Salesperson": s["sp"],
                     "Production Earned": prod, "Payout Earned": prod, "Trader Team Name": t["TraderAccountNumber"],
                     "Fidelity #": "", "ShortDesc": t["TraderAccountName"], "TradeType": t["OMReasonCode"],
                     "Trade Date": fMDY(t["trade_date_out"]), "RR Team": t["SalespersonName"], "Source": "Bloomberg XML",
                     "Sec Type": t["SECURITY_TYP"], "Sec Type Description": t["MARKET_SECTOR_DES"],
                     "Security Description": trim(t["Ticker"] + " " + t["MaturityDateExpirationDate"]),
                     "Gross Comms": gross, "Acct Short Description": fApos(t["CustomerAccountCounterparty"]),
                     "Currency": t["SecurityCurrencyISOCode"], "BuySell": t["BuySellCoverShortFlag"],
                     "TradeAmount": t["TradeAmount"], "GLCS CODE": "", "xml_modified": 1 if t["version_no"] > 1 else 0})
    # repo
    repo_file = pick_ranked(str(SD / "Operations" / "BroadridgeData" / "Reports" / ymd / "*"),
                            "YTDSalesCommission_|RepoSalesCommission_|YTDSalesComission_|RepoSalesComission_|YTDSalesCommission|RepoSalesCommission|YTDSalesComission|RepoSalesComission",
                            "@|.csv|.txt", False, ymd)
    if repo_file:
        hdr, rows = read_delimited(repo_file, ",", True, pick_charset(repo_file))
        cols = {k: pick_col(hdr, v) for k, v in {
            "td": "td|tradedate|asoftradedate", "account": "account|acct|accountname", "cusip": "cusip",
            "trans": "trans|transno|transnum|transnumber", "sales": "salesperson|salespersonname", "trader": "trader|tradername",
            "trtype": "trtype|tradetype", "asset": "assetclass|assettype", "secdesc": "securitydescription|securitydesc",
            "net": "netcredit|commission|grosscommission", "principal": "principal|tradeamount|paramount"}.items()}
        rr = []
        for i, r in enumerate(rows, 1):
            x = {k: col_text(r, c) for k, c in cols.items()}
            d = build_date(x["td"])
            x["split_date"] = d if d is not None else payout
            x["net_num"] = build_num(x["net"])
            x["row"] = i
            rr.append(x)
        for x, s in apply_split(rr, split, "sales", "split_date"):
            net = x["net_num"]
            prod_raw = None if net is None else net * s["split_num"]
            prod = None if net is None else (-0.000001 if (net < 0 and fRound2(prod_raw) == 0) else fRound2(prod_raw))
            rgross = None if net is None else (-0.000001 if (net < 0 and fRound2(net) == 0) else fRound2(net))
            tdo = fMDY(x["split_date"])
            core.append({"As of trade date": tdo, "Client": x["account"], "Security": x["cusip"], "Trade Id": x["trans"],
                         "Salesperson": s["sp"], "Production Earned": prod, "Payout Earned": prod, "Trader Team Name": x["trader"],
                         "Fidelity #": "", "ShortDesc": x["trader"], "TradeType": x["trtype"], "Trade Date": tdo,
                         "RR Team": x["sales"], "Source": "Repo", "Sec Type": x["asset"], "Sec Type Description": x["asset"],
                         "Security Description": x["secdesc"], "Gross Comms": rgross,
                         "Acct Short Description": fApos(x["account"]), "Currency": "USD", "BuySell": "B",
                         "TradeAmount": x["principal"], "GLCS CODE": "", "xml_modified": 0})
    # 12_Final: cross-year rule
    final = []
    for r in core:
        a = build_date(r["As of trade date"]); t = build_date(r["Trade Date"])
        ay = None if a is None else from_serial(a).year
        ty = None if t is None else from_serial(t).year
        if (ay is None or ay != 2026) and ty == 2026 and trim(r["ShortDesc"]).upper() in ("GNCL", "MULT", "GNPL"):
            continue
        final.append(r)
    # adjustments
    adj_file = pick_ranked(str(SD / "Qlikview" / "Sales" / "Data" / "adjustments*"),
                           "adjustments DailyExportOfPayout_|adjustments DailyExportOfPayout|adjustments_DailyExportOfPayout_|adjustments_DailyExportOfPayout|adjustmentsDailyExportOfPayout_|adjustmentsDailyExportOfPayout",
                           "@|.csv|.txt|.xlsx|.xlsm|.xls", True, ymd)
    if adj_file:
        hdr, rows = read_delimited(adj_file, ",", True, pick_charset(adj_file))
        cols = {c: pick_col(hdr, header_norm(c)) for c in OFFICIAL}
        for r in rows:
            x = {c: ("" if cols[c] is None or r.get(cols[c]) is None else r.get(cols[c])) for c in OFFICIAL}
            for c in ("Production Earned", "Payout Earned", "Gross Comms"):
                x[c] = build_num(x[c])
            x["xml_modified"] = 0
            final.append(x)
    # trade date of modified trades, 235 / TEST
    kept = []
    for r in final:
        if trim(r["Source"]).upper() == "BLOOMBERG XML" and r["xml_modified"] == 1:
            r["Trade Date"] = r["As of trade date"]
        if fTeamKey(r["RR Team"]) == "235" or fTeamKey(r["Client"]) == "TEST":
            continue
        kept.append(r)
    # GLCS
    for r in kept:
        if trim(r["Source"]).upper() != "BLOOMBERG XML":
            continue
        base, nz, clean = acct_keys(r["Acct Short Description"])
        if len(keepchar(clean, LETTERS)) > 0:
            r["GLCS CODE"] = clean
            continue
        if len(base) == 0:
            continue
        hit = direct.get(base) or direct.get(nz) or ""
        if not hit:
            for k in (base, nz):
                if k in sub:
                    _, _, ab, anz = sub[k]
                    hit = accnr.get(ab) or accnr.get(anz) or ""
                    if hit:
                        break
        if hit:
            r["GLCS CODE"] = hit
    out = FX / "sim_v12_payout.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(OFFICIAL)
        for r in kept:
            wr.writerow([money(r[c]) if c in ("Production Earned", "Payout Earned", "Gross Comms") else r[c] for c in OFFICIAL])
    print(f"payout date {ymd} | xml files {len(sel)} | trades {len(trades)} | after versioning {n_versioned} | active {len(active)} | split valid {len(split)} | final rows {len(kept)}")
    ref = SD / "Qlikview" / "Sales" / "Data" / "castine" / f"PPT_DailyExportOfPayout_{ymd}.csv"
    if not ref.exists():
        print("no Python reference file", ref)
        return 2
    with open(ref, newline="", encoding="utf-8") as f:
        py = list(csv.reader(f))
    with open(out, newline="", encoding="utf-8") as f:
        ql = list(csv.reader(f))
    same = py == ql
    print(f"python rows {len(py) - 1} | emulated qlik rows {len(ql) - 1} | identical cell by cell and in the same order: {same}")
    if not same:
        from collections import Counter
        cp, cq = Counter(map(tuple, py[1:])), Counter(map(tuple, ql[1:]))
        only_py = list((cp - cq).elements()); only_ql = list((cq - cp).elements())
        print(f"same rows ignoring order: {not only_py and not only_ql}")
        for r in only_py[:12]:
            print("  only in Python:", r)
        for r in only_ql[:12]:
            print("  only in Qlik  :", r)
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
