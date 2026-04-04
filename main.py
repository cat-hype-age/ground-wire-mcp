"""Ground Wire MCP Server — Cloud Run. SSE transport, 7 tools."""
import asyncio, json, os, uuid
from pathlib import Path
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from sse_starlette.sse import EventSourceResponse

# --- Corpus Index ---
try:
    with open(Path(__file__).parent / "corpus_index.json") as f: INDEX = json.load(f)
    FILES,TEMPORAL,TABLE_CODES=INDEX["files"],INDEX["temporal"],INDEX["table_codes"]
    TABLE_NAMES,KEYWORDS,TOPICS=INDEX["table_names"],INDEX["keywords"],INDEX["topics"]
    COK=True
except Exception as e:
    print(f"Warning: {e}"); FILES=TEMPORAL=TABLE_CODES=TABLE_NAMES=KEYWORDS=TOPICS={}; COK=False

# --- CPI-U ---
CPI={1939:13.9,1940:14.0,1941:14.7,1942:16.3,1943:17.3,1944:17.6,1945:18.0,1946:19.5,1947:22.3,1948:24.1,1949:23.8,1950:24.1,1951:26.0,1952:26.5,1953:26.7,1954:26.9,1955:26.8,1956:27.2,1957:28.1,1958:28.9,1959:29.1,1960:29.6,1961:29.9,1962:30.2,1963:30.6,1964:31.0,1965:31.5,1966:32.4,1967:33.4,1968:34.8,1969:36.7,1970:38.8,1971:40.5,1972:41.8,1973:44.4,1974:49.3,1975:53.8,1976:56.9,1977:60.6,1978:65.2,1979:72.6,1980:82.4,1981:90.9,1982:96.5,1983:99.6,1984:103.9,1985:107.6,1986:109.6,1987:113.6,1988:118.3,1989:124.0,1990:130.7,1991:136.2,1992:140.3,1993:144.5,1994:148.2,1995:152.4,1996:156.9,1997:160.5,1998:163.0,1999:166.6,2000:172.2,2001:177.1,2002:179.9,2003:184.0,2004:188.9,2005:195.3,2006:201.6,2007:207.3,2008:215.3,2009:214.5,2010:218.1,2011:224.9,2012:229.6,2013:233.0,2014:236.7,2015:237.0,2016:240.0,2017:245.1,2018:251.1,2019:255.7,2020:258.8,2021:270.9,2022:292.7,2023:304.7,2024:313.5,2025:320.2}
CPIM={1946:{1:18.2,2:18.2,3:18.3,4:18.4,5:18.5,6:18.7,7:20.0,8:20.4,9:20.4,10:20.8,11:21.2,12:21.5},1947:{1:21.5,2:21.5,3:21.9,4:21.9,5:21.9,6:22.0,7:22.2,8:22.5,9:23.0,10:23.0,11:23.1,12:23.4},1948:{1:23.7,2:23.5,3:23.4,4:23.8,5:23.9,6:24.1,7:24.4,8:24.5,9:24.5,10:24.4,11:24.2,12:24.1},1949:{1:24.0,2:23.8,3:23.8,4:23.9,5:23.8,6:23.9,7:23.7,8:23.7,9:23.9,10:23.7,11:23.8,12:23.5},1969:{1:34.1,2:34.2,3:34.5,4:34.7,5:34.9,6:35.2,7:35.4,8:35.6,9:35.8,10:36.0,11:36.3,12:36.6},1979:{1:68.3,2:69.1,3:69.8,4:70.6,5:71.5,6:72.3,7:73.1,8:73.8,9:74.6,10:75.2,11:75.9,12:76.7},1980:{1:77.8,2:78.9,3:80.1,4:81.0,5:81.8,6:82.7,7:82.7,8:83.3,9:84.0,10:84.8,11:85.5,12:86.3},1981:{1:87.0,2:87.9,3:88.5,4:89.1,5:89.8,6:90.6,7:91.6,8:92.3,9:93.2,10:93.4,11:93.7,12:94.0}}

# --- FX ---
USD_GBP={1939:4.03,1940:3.83,1941:4.03,1942:4.03,1943:4.03,1944:4.03,1945:4.03,1946:4.03,1947:4.03,1948:4.03,1949:3.69,1950:2.80,1951:2.80,1952:2.80,1953:2.81,1954:2.81,1955:2.79,1956:2.80,1957:2.79,1958:2.81,1959:2.81,1960:2.81,1961:2.80,1962:2.81,1963:2.80,1964:2.79,1965:2.80,1966:2.79,1967:2.75,1968:2.39,1969:2.39,1970:2.40,1971:2.44,1972:2.50,1973:2.45,1974:2.34,1975:2.22,1976:1.805,1977:1.745,1978:1.919,1979:2.122,1980:2.325,1981:2.025,1982:1.749,1983:1.516,1984:1.337,1985:1.298,1990:1.784,1991:1.767,1992:1.766,1993:1.502,1994:1.532,1995:1.578,1996:1.561,2000:1.516,2001:1.440,2002:1.503,2005:1.820,2010:1.546,2015:1.529,2016:1.356}
USD_DEM={1960:0.238,1965:0.250,1970:0.274,1971:0.289,1972:0.313,1973:0.374,1974:0.382,1975:0.407,1976:0.397,1977:0.431,1978:0.495,1979:0.546,1980:0.553,1985:0.338}
INR_USD={1960:4.76,1961:4.76,1962:4.76,1963:4.76,1964:4.76,1965:4.76,1966:6.36,1970:7.50,1975:8.38,1980:7.86,1985:12.37,1990:17.50,1995:32.43,2000:44.94}
JPY_USD={1960:360.0,1970:360.0,1975:296.8,1980:226.7,1985:238.5,1990:144.8,1995:94.1,2000:107.8,2004:108.2,2010:87.8,2015:121.0,2016:108.8,2020:106.8,2025:149.3}
CAD_USD={1955:1.01,1959:1.04,1960:1.03,1965:1.08,1970:1.04,1975:1.017,1980:1.169,1985:1.366,1990:1.167,2000:1.485}
FXD={"USD/GBP":{"d":USD_GBP,"n":"USD per GBP"},"USD/DEM":{"d":USD_DEM,"n":"USD per DEM"},"INR/USD":{"d":INR_USD,"n":"INR per USD"},"JPY/USD":{"d":JPY_USD,"n":"JPY per USD"},"CAD/USD":{"d":CAD_USD,"n":"CAD per USD"}}
FXA={"GBP":"USD/GBP","POUND":"USD/GBP","STERLING":"USD/GBP","GBP/USD":"USD/GBP","USDGBP":"USD/GBP","DEM":"USD/DEM","MARK":"USD/DEM","DEM/USD":"USD/DEM","USDDEM":"USD/DEM","INR":"INR/USD","RUPEE":"INR/USD","INRUSD":"INR/USD","USD/INR":"INR/USD","JPY":"JPY/USD","YEN":"JPY/USD","JPYUSD":"JPY/USD","USD/JPY":"JPY/USD","CAD":"CAD/USD","CADUSD":"CAD/USD","USD/CAD":"CAD/USD"}

# --- Handlers ---
def h_search(a):
    topic,kw,lim=a.get("topic","").lower(),a.get("keyword","").lower(),a.get("limit",20)
    r=set()
    if topic:
        for tn,td in TOPICS.items():
            if topic in tn or any(topic in k for k in td["keywords"]):
                for c in td["codes"]: r.update(e["file"] for e in TABLE_CODES.get(c,[]))
    s=kw or topic
    if s:
        for k,fs in KEYWORDS.items():
            if any(w in k for w in s.split()): r.update(fs)
    if not r: return f"No files for topic='{topic}' keyword='{kw}'"
    sf=sorted(r,key=lambda f:(FILES.get(f,{}).get("year",0),f),reverse=True)[:lim]
    return f"Found {len(r)} files (showing {len(sf)}):\n"+"\n".join(f"  {f}  (yr={FILES.get(f,{}).get('year')}, mo={FILES.get(f,{}).get('month')})" for f in sf)

def h_tables(a):
    code,pat,yr,lim=a.get("code","").upper(),a.get("pattern","").lower(),a.get("year"),a.get("limit",20)
    r=[]
    if code:
        for e in TABLE_CODES.get(code,[]):
            if yr and FILES.get(e["file"],{}).get("year")!=yr: continue
            nm=next((t[2] for t in TABLE_NAMES.get(e["file"],[]) if t[0]==e["line"]),"")
            r.append({"f":e["file"],"l":e["line"],"c":code,"n":nm})
    if pat and not r:
        for fn,ts in TABLE_NAMES.items():
            if yr and FILES.get(fn,{}).get("year")!=yr: continue
            for t in ts:
                if pat in t[2].lower(): r.append({"f":fn,"l":t[0],"c":t[1] or "","n":t[2]})
    if not r: return f"No tables for code='{code}' pattern='{pat}'"
    r=sorted(r,key=lambda x:(x["f"],x["l"]))[:lim]
    return f"Found {len(r)} table(s):\n"+"\n".join(f"  {x['f']} line {x['l']}: [{x['c']}] {x['n']}" for x in r)

def h_period(a):
    yr,mo,fy=a.get("year"),a.get("month"),a.get("fiscal_year")
    if fy:
        fy=int(fy); tys=[str(fy-1),str(fy)]
        fs=[f for ty in tys for f in TEMPORAL.get(ty,[])]
        return f"FY{fy} ends {'Jun 30' if fy<=1976 else 'Sep 30'}.\n"+"\n".join(f"  {f} (mo={FILES.get(f,{}).get('month')})" for f in sorted(fs))
    if yr:
        fs=TEMPORAL.get(str(yr),[])
        if not fs: return f"No files for year {yr}"
        if mo: fs2=[f for f in fs if FILES.get(f,{}).get("month")==int(mo)]; fs=fs2 if fs2 else fs
        return f"Files for {yr}:\n"+"\n".join(f"  {f} (mo={FILES.get(f,{}).get('month')})" for f in sorted(fs))
    return "Specify year, month, or fiscal_year."

def h_info(a):
    fn=a.get("filename",""); m=FILES.get(fn)
    if not m:
        ms=[f for f in FILES if fn.lower() in f.lower()]
        return f"Not found: '{fn}'. Try: {', '.join(ms[:5])}" if ms else f"Not found: '{fn}'"
    ts=TABLE_NAMES.get(fn,[])
    return f"{fn}: yr={m['year']} mo={m['month']} era={m['era']} lines={m['lines']} tables={m['table_count']}\n"+"\n".join(f"  L{t[0]}: [{t[1]}] {t[2]}" for t in sorted(ts,key=lambda x:x[0]))

def h_cpi(a):
    yr,mo=int(a.get("year",0)),a.get("month")
    if mo:
        mo=int(mo); ml=CPIM.get(yr)
        if ml and mo in ml: return f"CPI-U {yr}-{mo:02d}: {ml[mo]} (1982-84=100)"
        if yr in CPI: return f"No monthly for {yr}-{mo:02d}. Annual: {CPI[yr]}"
        return f"No CPI for {yr}"
    if yr in CPI:
        r=f"CPI-U {yr}: {CPI[yr]} (annual avg, 1982-84=100)"
        if yr in CPIM: r+=f"\nMonthly: {', '.join(f'{m}={v}' for m,v in sorted(CPIM[yr].items()))}"
        return r
    return f"No CPI for {yr}. Range: 1939-2025."

def h_fx(a):
    pair,yr=a.get("pair","").upper().replace(" ",""),a.get("year")
    n=FXA.get(pair,pair); ri=FXD.get(n)
    if not ri: return f"Unknown: '{pair}'. Available: {list(FXD.keys())}"
    d=ri["d"]
    if yr:
        yr=int(yr)
        if yr in d: return f"{n} {yr}: {d[yr]} ({ri['n']})"
        ys=sorted(d); b=[y for y in ys if y<=yr]; a2=[y for y in ys if y>=yr]
        near=([f"{b[-1]}:{d[b[-1]]}"] if b else [])+([f"{a2[0]}:{d[a2[0]]}"] if a2 else [])
        return f"No {n} for {yr}. Nearest: {', '.join(near)}"
    return f"{n} ({ri['n']}):\n"+"\n".join(f"  {y}: {d[y]}" for y in sorted(d))

def h_adj(a):
    v,fy,ty=float(a["value"]),int(a["from_year"]),int(a["to_year"])
    if fy not in CPI: return f"No CPI for {fy}"
    if ty not in CPI: return f"No CPI for {ty}"
    adj=v*(CPI[ty]/CPI[fy])
    return f"${v:,.2f} in {fy} = ${adj:,.2f} in {ty}\n{v}*({CPI[ty]}/{CPI[fy]})={adj:.2f}"

TOOLS=[
    {"name":"search_files_by_topic","description":"Find Treasury Bulletin files by topic/keyword.","inputSchema":{"type":"object","properties":{"topic":{"type":"string"},"keyword":{"type":"string"},"limit":{"type":"integer","default":20}}}},
    {"name":"find_tables","description":"Find tables by code (FFO-1, FD-3) or name pattern.","inputSchema":{"type":"object","properties":{"code":{"type":"string"},"pattern":{"type":"string"},"year":{"type":"integer"},"limit":{"type":"integer","default":20}}}},
    {"name":"get_files_for_period","description":"Get bulletins for a year/month/fiscal year.","inputSchema":{"type":"object","properties":{"year":{"type":"integer"},"month":{"type":"integer"},"fiscal_year":{"type":"integer"}}}},
    {"name":"get_file_info","description":"Get metadata and tables for a bulletin file.","inputSchema":{"type":"object","properties":{"filename":{"type":"string"}},"required":["filename"]}},
    {"name":"lookup_cpi","description":"CPI-U (1982-84=100) for a year (+optional month).","inputSchema":{"type":"object","properties":{"year":{"type":"integer"},"month":{"type":"integer"}},"required":["year"]}},
    {"name":"lookup_exchange_rate","description":"Exchange rate. Pairs: USD/GBP, USD/DEM, INR/USD, JPY/USD, CAD/USD.","inputSchema":{"type":"object","properties":{"pair":{"type":"string"},"year":{"type":"integer"}},"required":["pair"]}},
    {"name":"inflation_adjust","description":"Inflation-adjust value between years using CPI-U.","inputSchema":{"type":"object","properties":{"value":{"type":"number"},"from_year":{"type":"integer"},"to_year":{"type":"integer"}},"required":["value","from_year","to_year"]}},
]
H={"search_files_by_topic":h_search,"find_tables":h_tables,"get_files_for_period":h_period,"get_file_info":h_info,"lookup_cpi":h_cpi,"lookup_exchange_rate":h_fx,"inflation_adjust":h_adj}

# --- SSE Transport ---
S: dict[str, asyncio.Queue] = {}

async def sse_ep(req: Request):
    sid=str(uuid.uuid4()); q: asyncio.Queue=asyncio.Queue(); S[sid]=q
    url=f"{str(req.base_url).rstrip('/')}/messages?session_id={sid}"
    async def gen():
        yield {"event":"endpoint","data":url}
        try:
            while True:
                try: yield {"event":"message","data":json.dumps(await asyncio.wait_for(q.get(),timeout=300))}
                except asyncio.TimeoutError: yield {"event":"ping","data":""}
        except asyncio.CancelledError: pass
        finally: S.pop(sid,None)
    return EventSourceResponse(gen())

async def msg_ep(req: Request):
    sid=req.query_params.get("session_id")
    if not sid or sid not in S: return JSONResponse({"error":"bad session"},status_code=400)
    q=S[sid]; b=await req.json(); method,mid,p=b.get("method",""),b.get("id"),b.get("params",{})
    resp=None
    if method=="initialize":
        resp={"jsonrpc":"2.0","id":mid,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"ground-wire-tools","version":"1.0.0"}}}
    elif method=="tools/list":
        resp={"jsonrpc":"2.0","id":mid,"result":{"tools":TOOLS}}
    elif method=="tools/call":
        h=H.get(p.get("name",""))
        if h:
            try: resp={"jsonrpc":"2.0","id":mid,"result":{"content":[{"type":"text","text":h(p.get("arguments",{}))}]}}
            except Exception as e: resp={"jsonrpc":"2.0","id":mid,"result":{"content":[{"type":"text","text":f"Error: {e}"}]}}
        else: resp={"jsonrpc":"2.0","id":mid,"error":{"code":-32601,"message":f"Unknown: {p.get('name')}"}}
    elif method!="notifications/initialized" and mid: resp={"jsonrpc":"2.0","id":mid,"error":{"code":-32601,"message":f"Unknown: {method}"}}
    if resp: await q.put(resp)
    return Response(status_code=202)

async def health(req: Request): return JSONResponse({"status":"ok","tools":7,"corpus":COK})

app=Starlette(routes=[Route("/sse",sse_ep),Route("/messages",msg_ep,methods=["POST"]),Route("/health",health),Route("/",health)])

if __name__=="__main__":
    import uvicorn; uvicorn.run(app,host="0.0.0.0",port=int(os.environ.get("PORT",8080)))
