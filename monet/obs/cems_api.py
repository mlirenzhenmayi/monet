from __future__ import print_function
import os
import datetime
import pandas as pd
import numpy as np
import requests
import json
import sys
import seaborn as sns
import monet.obs.obs_util as obs_util

"""
NAME: cems_api.py
PGRMMER: Alice Crawford   ORG: ARL
This code written at the NOAA air resources laboratory
Python 3
#################################################################

Classes:
----------

CEMS

helper classes for CEMS

Emissions
FacilitiesData
MonitoringPlan


Functions:
----------

addquarter
get_datelist
findquarter

sendrequest

"""


def sendrequest(rqq, key):
    """
    Method for sending requests to the EPA API
    Inputs :
    --------
    rqq : string
          request string.
    Returns:
    --------
    data : response object
    """
    apiurl = "https://api.epa.gov/FACT/1.0/"
    rqq = apiurl + rqq + "?api_key=" + key
    print("Request: ", rqq)
    data = requests.get(rqq)
    print("Status Code", data.status_code)
    return data


def addquarter(rdate):
    """
    INPUT
    rdate : datetime object
    RETURNS
    newdate : datetime object
    requests for emissions are made per quarter.
    Returns first date in the next quarter from the input date.
    """
    quarter = findquarter(rdate)
    quarter += 1
    year = rdate.year
    if quarter > 4:
        quarter = 1
        year += 1
    month = 3 * quarter - 2
    newdate = datetime.datetime(year, month, 1, 0)
    return newdate


def get_datelist(rdate):
    """
    INPUT
    rdate : tuple of datetime objects
    (start date, end date)
    RETURNS:
    rdatelist : list of datetimes.

    Return list of first date in each quarter from
    startdate to end date.
    """
    if isinstance(rdate, list):
        r1 = rdate[0]
        r2 = rdate[1]
        rdatelist = [r1]
        done = False
        iii = 0
        while not done:
            r3 = addquarter(rdatelist[-1])
            if r3 <= r2:
                rdatelist.append(r3)
            else:
                done = True
            if iii > 100:
                done = True
            iii += 1
    else:
        rdatelist = [rdate]
    return rdatelist


def findquarter(idate):
    if idate.month <= 3:
        qtr = 1
    elif idate.month <= 6:
        qtr = 2
    elif idate.month <= 9:
        qtr = 3
    elif idate.month <= 12:
        qtr = 4
    return qtr


def columns_rename(columns, verbose=False):
    """
    Maps columns with one name to a standard name
    Parameters:
    ----------
    columns: list of strings

    Returns:
    --------
    rcolumn: list of strings
    """
    rcolumn = []
    for ccc in columns:
        if "facility" in ccc.lower() and "name" in ccc.lower():
            rcolumn.append("facility_name")
        elif "oris" in ccc.lower():
            rcolumn.append("oris")
        elif "facility" in ccc.lower() and "id" in ccc.lower():
            rcolumn.append("fac_id")
        elif (
            "so2" in ccc.lower()
            and ("lbs" in ccc.lower() or "pounds" in ccc.lower())
            and ("rate" not in ccc.lower())
        ):
            rcolumn.append("so2_lbs")
        elif (
            "nox" in ccc.lower()
            and ("lbs" in ccc.lower() or "pounds" in ccc.lower())
            and ("rate" not in ccc.lower())
        ):
            rcolumn.append("nox_lbs")
        elif "co2" in ccc.lower() and (
            "short" in ccc.lower() and "tons" in ccc.lower()
        ):
            rcolumn.append("co2_short_tons")
        elif "date" in ccc.lower():
            rcolumn.append("date")
        elif "hour" in ccc.lower():
            rcolumn.append("hour")
        elif "lat" in ccc.lower():
            rcolumn.append("latitude")
        elif "lon" in ccc.lower():
            rcolumn.append("longitude")
        else:
            rcolumn.append(ccc.strip().lower())
    return rcolumn


class Emissions:
    # NOTES
    # BAF - bias adjustment factor
    # MEC - maximum expected concentraiton
    # MPF - maximum potential stack gas flow rate
    # monitoring plan specified monitor range.

    def __init__(self, key):
        self.df = pd.DataFrame()
        self.key = key
        self.orislist = []
        self.unithash = {}
        self.so2name = "SO2CEMReportedAdjustedSO2"
        self.so2nameB = "UnadjustedSO2"

    def add(
        self,
        oris,
        locationID,
        year,
        quarter,
        ifile="efile.txt",
        verbose=False,
        stackht=None,
        logfile="warnings.emit.txt",
    ):
        """
        oris : int
        locationID : str
        year : int
        quarter : int
        ifile : str

        """
        if oris not in self.orislist:
            self.orislist.append(oris)
        if oris not in self.unithash.keys():
            self.unithash[oris] = []
        self.unithash[oris].append(locationID)

        # if locationID == None:
        #   unitra = self.get_units(oris)
        # else:
        #   unitra = [locationID]
        if int(quarter) > 4:
            print("Warning: quarter greater than 4")
            sys.exit()
        tra = []
        # print('Units at facility', unitra)
        # unitra = sorted(set(unitra))
        # if not unitra:
        #   print('oris not in ', self.facdf['oris'].unique())
        #   sys.exit()
        # ----------------------------------------------------
        # for locationID in unitra:
        locationID = str(locationID)
        efile = "efile.txt"
        estr = "emissions/hourlyData/csv"
        oris = str(oris)
        getstr = "/".join([estr, str(oris), locationID, str(year), str(quarter)])
        data = sendrequest(getstr, self.key)
        if data.status_code != 200:
            return data.status_code
        iii = 0
        cols = []
        for line in data.iter_lines(decode_unicode=True):
            if iii == 0:
                tcols = line.split(",")
                tcols.append("unit id")
                tcols.append("stackht")
                tcols.append("oris")
                if verbose:
                    with open("headers.txt", "w") as fid:
                        for val in tcols:
                            fid.write(val + "\n")
                    # print('press a key to continue ')
                    # input()
                if self.so2name not in tcols:
                    with open(logfile, "a") as fid:
                        rstr = "ORIS " + str(oris)
                        rstr += "mid " + str(locationID) + "\n"
                        rstr += "NO adjusted SO2 data \n"
                        if self.so2nameB not in tcols:
                            rstr += "NO SO2 data \n"
                        rstr += "------------------------\n"
                        fid.write(rstr)
                    print("--------------------------------------")
                    print("UNIT" + str(locationID) + " no SO2 data")
                    print("--------------------------------------")
                    return -999
                else:
                    cols = tcols
            else:
                lt = line.split(",")
                lt.append(locationID)
                lt.append(float(stackht))
                lt.append(int(oris))
                tra.append(lt)
            iii += 1
            with open(efile, "a") as fid:
                fid.write(line)
        # ----------------------------------------------------
        df = pd.DataFrame(tra, columns=cols)
        # print(df[0:10])
        df.apply(pd.to_numeric, errors="ignore")
        df = self.manage_date(df)
        df = self.convert_cols(df)
        if self.df.empty:
            self.df = df
        else:
            self.df = self.df.append(df)
        return data.status_code

    def get_so2(self):
        keep = [
            "DateHour",
            "OperatingTime",
            "HourLoad",
            "u so2_lbs",
            "so2_lbs",
            "AdjustedFlow",
            "UnadjustedFlow",
            "FlowMODC",
            "SO2MODC",
            "unit id",
            "stackht",
            "oris",
        ]
        tcols = self.df.columns.values
        tdrop = np.setdiff1(tcols, keep)
        tempdf = self.df.drop(tdrop, axis=1)
        columns = columns_rename(tempdf.columns.values)
        tempdf.columns = columns
        return tempdf

    def convert_cols(self, df):
        """
        OperatingTime : fraction of the clock hour during which the unit
                        combusted any fuel. If unit, stack or pipe did not
                        operate report 0.00.
        """

        def simpletofloat(xxx):
            try:
                rt = float(xxx)
            except BaseException:
                rt = -999
            return rt

        def tofloat(optime, cname):
            if optime == 0:
                rval = 0
            else:
                try:
                    rval = float(cname)
                except BaseException:
                    rval = -999
            return rval

        # map OperatingTime to a float
        df["OperatingTime"] = df["OperatingTime"].map(simpletofloat)
        df["AdjustedFlow"] = df["AdjustedFlow"].map(simpletofloat)
        # map SO2 data to a float
        # if operating time is zero then map to 0 (it is '' in file)
        optime = "OperatingTime"
        cname = "UnadjustedSO2"
        df["u so2_lbs"] = df.apply(lambda row: tofloat(row[optime], row[cname]), axis=1)
        cname = "SO2CEMReportedAdjustedSO2"
        df["so2_lbs"] = df.apply(lambda row: tofloat(row[optime], row[cname]), axis=1)

        # temp is values that are not valid
        temp = df[df["u so2_lbs"].isin([-999])]
        temp = temp[temp["OperatingTime"] > 0]
        print("Values that cannot be converted to float")
        print(temp[cname].unique())
        print("MODC ", temp["SO2MODC"].unique())
        ky = "MATSSstartupshutdownflat"
        if ky in temp.keys():
            print("MATSSstartupshutdownflat", temp["MATSStartupShutdownFlag"].unique())
        # print(temp['date'].unique())

        ky = "Operating Time"
        if ky in temp.keys():
            print("Operating Time", temp["OperatingTime"].unique())
        if ky in df.keys():
            print("All op times", df["OperatingTime"].unique())
        # for line in temp.iterrows():
        #    print(line)
        return df

    def manage_date(self, df):
        """DateHour field is originally in string form 4/1/2016 02:00:00 PM
           Here, change to a datetime object.
        """
        # Using the %I for the hour field and %p for AM/Pm converts time
        # correctly.
        def newdate(xxx):
            fmt = "%m/%d/%Y %I:%M:%S %p"
            try:
                rdt = datetime.datetime.strptime(xxx["DateHour"], fmt)
            except BaseException:
                print("PROBLEM DATE", xxx["DateHour"])
                rdt = datetime.datetime(1700, 1, 1, 0)
            return rdt

        df["date"] = df.apply(newdate, axis=1)
        return df

    def plot(self):
        import matplotlib.pyplot as plt

        print("plot emissions")
        df = self.df.copy()
        # print(df['date'][0:10])
        # print(df['USO2'][0:10])
        # print(type(df['USO2'][0]))
        # plt.plot(df['date'][0:100], df['USO2'][0:100], '-b.')
        temp1 = df[df["date"].dt.year != 1700]
        sns.set()
        for unit in df["unit id"].unique():
            temp = temp1[temp1["unit id"] == unit]
            temp = temp[temp["SO2MODC"].isin(["01", "02", "03", "04"])]
            plt.plot(temp["date"], temp["so2_lbs"], label=str(unit))
            print("UNIT", str(unit))
            print(temp["SO2MODC"].unique())
        for unit in df["unit id"].unique():
            temp = temp1[temp1["unit id"] == unit]
            temp = temp[temp["SO2MODC"].isin(["01", "02", "03", "04"]) == False]
            plt.plot(temp["date"], temp["so2_lbs"], label="bad " + str(unit))
            print("UNIT", str(unit))
            print(temp["SO2MODC"].unique())
        ax = plt.gca()
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels)
        plt.show()
        for unit in df["unit id"].unique():
            temp = temp1[temp1["unit id"] == unit]
            print("BAF", temp["FlowBAF"].unique())
            print("MODC", temp["FlowMODC"].unique())
            print("PMA", temp["FlowPMA"].unique())
            plt.plot(temp["date"], temp["AdjustedFlow"], label=str(unit))
        plt.show()


class MonitoringPlan:
    def __init__(self, oris, mid, key):
        self.df = pd.DataFrame()
        self.oris = oris  # oris code of facility
        self.mid = mid  # monitoring location id.
        self.key = key
        self.stackht = None

    def printall(self):
        data = self.get(oris, mid, date)
        jobject = data.json()
        rstr = unpack_response(jobject)
        return rstr

    def get(self, date):
        """
        Request to get monitoring plans for oris code and locationID.
        locationIDs for an oris code can be found in

        oris : int
        locationID : str or int
        date : datetime object

        The monitoring plan has locationAttributes which
        include the stackHeight, crossAreaExit, crossAreaFlow.

        It also includes monitoringSystems which includes
        ststeymTypeDescription (such as So2 Concentration)

        QuarterlySummaries gives so2Mass each quarter.
        """
        oris = self.oris
        mid = self.mid
        dstr = date.strftime("%Y-%m-%d")
        mstr = "monitoringplan"
        getstr = "/".join([mstr, str(oris), str(mid), dstr])
        data = sendrequest(getstr, self.key)
        if data.status_code != 200:
            return None
        jobject = data.json()
        dhash = self.unpack(jobject["data"])
        return dhash

    def unpack(self, dhash):
        """
        dhash :
        Returns:

        df : pandas dataframe
        Information for one oris code.
        columns
        stackname, unit, stackheight, crossAreaExit,
        crossAreaFlow, locID, isunit
        """
        dlist = []
        print(dhash.keys())
        stackname = dhash["unitStackName"]
        for unit in dhash["monitoringLocations"]:
            for att in unit["locationAttributes"]:
                dhash = {}
                dhash["stackname"] = stackname
                dhash["unit"] = unit
                dhash["stackht"] = att["stackHeight"]  # int
                dhash["crossAreaExit"] = att["crossAreaExit"]  # int
                dhash["crossAreaFlow"] = att["crossAreaFlow"]  # int
                dhash["locID"] = att["locId"]
                dhash["isunit"] = att["isUnit"]
                dlist.append(dhash)
        # self.df = pd.DataFrame(dlist)
        return dlist

        # Then have list of dicts
        #  unitOperations
        #  unitPrograms
        #  unitFuels
        # TO DO need to change this so don't overwrite if more than one fuel.


#       for fuel in unit['unitFuels']:
#           chash={}
#           chash['fuel'] = fuel['fuelCode']
#           chash['fuelname'] = fuel['fuelDesc']
#           chash['fuelindCode'] = fuel['indCode']
#  unitControls
#  monitoringMethods
#      for method in unit['monitoringMethods']:
#           bhash={}
#           if method['parameterCode'] == 'SO2':
#               bhash['methodCode'] = method['methodCode']
#               bhash['subDataCode'] = method['subDataCode']
# mercuryToxicsStandardsMethods
# spanDetails
# systemFlows
# analyzerRanges

# emissionsFormulas
#       for method in unit['emissionsFormulas']:
#           if method['parameterCode'] == 'SO2':
#               bhash['equationCode'] = method['equationCode']

# rectangularDuctWallEffectAdjustmentFactors
# loadlevels (load levels for different date ranges)
# monitoringDefaults

# ******
# monitoringSystems
# some systems may be more accurate than others.
# natural gas plants emissions may have less uncertainty.


# monitoringQualifications

# quarterlySummaries
# emissionSummaries

# owners
# qaTestSummaries
# reportingFrequencies

# unitStackConfigurations
# comments
# contacts
# responsibilities


class FacilitiesData:
    def __init__(self, key):
        self.df = pd.DataFrame()
        self.key = key
        self.get()
        # self.oris = oris   #oris code of facility
        # self.mid = mid     #monitoring location id.

    def printall(self):
        getstr = "facilities"
        data = sendrequest(getstr, self.key)
        jobject = data.json()
        rstr = unpack_response(jobject)
        return rstr

    def get(self):
        """
        Request to get facilities information
        """
        getstr = "facilities"
        data = sendrequest(getstr, self.key)
        jobject = data.json()
        self.df = self.unpack(jobject)
        # return(data)

    def oris_by_area(self, llcrnr, urcrnr):
        """
        llcrnr : tuple (float,float)
        urcrnr : tuple (float,float)
        """
        dftemp = obs_util.latlonfilter(self.df, llcrnr, urcrnr)
        orislist = dftemp["oris"].unique()
        return orislist

    def get_units(self, oris):
        """
        oris : int
        Returns list of monitoring location ids
        """
        oris = int(oris)
        if self.df.empty:
            self.facdata()
        temp = self.df[self.df["oris"] == oris]
        units = temp["unit"].unique()
        return units

    def unpack(self, dhash):
        """
        iterates through a response which contains nested dictionaries and lists.
        # facilties 'data' is a list of dictionaries.
        # there is one dictionary for each oris code.
        # Each dictionary has a list under the key monitoringLocations.
        # each monitoryLocation has a name which is what is needed
        # for the locationID input into the get_emissions.
        """
        dlist = []

        # originally just used one dictionary but if doing
        # a['dog'] = 1
        # dlist.append(a)
        # a['dog'] = 2
        # dlist.append(a)
        # for some reason dlist will then update the dictionary and will get
        # dlist = [{'dog': 2}, {'dog':2}] instead of
        # dlist = [{'dog': 1}, {'dog':2}]

        for val in dhash["data"]:
            ahash = {}
            ahash["oris"] = int(val["orisCode"])
            ahash["name"] = val["name"]
            ahash["latitude"] = val["geographicLocation"]["latitude"]
            ahash["longitude"] = val["geographicLocation"]["longitude"]
            for sid in val["monitoringPlans"]:
                bhash = {}
                if sid["status"] == "Active":
                    bhash["begin time"] = sid["beginYearQuarter"]
                    bhash["end time"] = sid["endYearQuarter"]
                    for unit in sid["monitoringLocations"]:
                        chash = {}
                        chash["unit"] = unit["name"]
                        chash["isunit"] = unit["isUnit"]
                        chash.update(ahash)
                        chash.update(bhash)
                        dlist.append(chash)
        df = pd.DataFrame(dlist)
        return df


def unpack_response(dhash, deep=100, pid=0):
    """
    iterates through a response which contains nested dictionaries and lists.
    dhash: dictionary which may be nested.
    deep: int
        indicated how deep to print out nested levels.
    pid : int

    """
    rstr = ""
    for k2 in dhash.keys():
        iii = pid
        spc = " " * iii
        rstr += spc + str(k2) + " " + str(type(dhash[k2])) + " : "
        # UNPACK DICTIONARY
        if iii < deep and isinstance(dhash[k2], dict):
            rstr += "\n"
            iii += 1
            rstr += spc
            rstr += unpack_response(dhash[k2], pid=iii)
            rstr += "\n"
        # UNPACK LIST
        elif isinstance(dhash[k2], list):
            iii += 1
            rstr += "\n---BEGIN LIST---" + str(iii) + "\n"
            for val in dhash[k2]:
                if isinstance(val, dict):
                    rstr += unpack_response(val, deep=deep, pid=iii)
                    rstr += "\n"
                else:
                    rstr += spc + "listval " + str(val) + str(type(val)) + "\n"
            rstr += "---END LIST---" + str(iii) + "\n"
        elif isinstance(dhash[k2], str):
            rstr += spc + dhash[k2] + "\n"
        elif isinstance(dhash[k2], int):
            rstr += spc + str(dhash[k2]) + "\n"
        elif isinstance(dhash[k2], float):
            rstr += spc + str(dhash[k2]) + "\n"
        else:
            rstr += "\n"
    return rstr


def get_stack_dict(df, orispl=None):
    """
    Parameters
    ----------
    df dataframe created with stack_height() call
    orispl : list
           list of orispl codes to consider
    Returns
    -------
    stackhash: dictionary
    key orispl code and value list of tuples with
    (stackid, stackht (in feet))
    """
    stackhash = {}
    df = df[df["oris"].isin(orispl)]
    # df = df[['oris', 'boilerid', 'stackht','stackdiam']]

    def newc(x):
        return (
            x["boilerid"],
            x["stackht"],
            x["stackdiam"],
            x["stacktemp"],
            x["stackvel"],
        )

    for oris in df["oris"].unique():
        dftemp = df[df["oris"] == oris]
        dftemp["tuple"] = dftemp.apply(newc, axis=1)
        value = dftemp["tuple"].unique()
        stackhash[oris] = value
    return stackhash


def max_stackht(df, meters=True, verbose=False):
    """
       adds 'max_stackht' column to dataframe returned by stack_height function.
       this column indicates the largest stack height associated with that
       orispl code.
    """
    df2 = pd.DataFrame()
    iii = 0
    mult = 1
    if meters:
        mult = 0.3048
    for orispl in df["oris"].unique():
        dftemp = df[df["oris"] == orispl]
        slist = mult * np.array(dftemp["stackht"].unique())

        maxval = np.max(slist)
        dftemp["max_stackht"] = maxval
        dftemp.drop(["stackht", "stackdiam"], inplace=True, axis=1)
        dftemp.drop_duplicates(inplace=True)
        # dftemp['list_stackht'] = 0
        # dftemp.at[orispl, 'list_stackht'] =  list(slist)

        if iii == 0:
            df2 = dftemp.copy()
        else:
            df2 = pd.concat([df2, dftemp], axis=0)
        iii += 1
        if verbose:
            print("ORISPL", orispl, maxval, slist)
        # print(dftemp['list_stackht'].unique())
    return df2


class CEMS(object):
    """
    Class for data from continuous emission monitoring systems (CEMS).
    Data from power plants can be downloaded from
    ftp://newftp.epa.gov/DMDNLoad/emissions/

   Attributes
    ----------
    efile : type string
        Description of attribute `efile`.
    url : type string
        Description of attribute `url`.
    info : type string
        Information about data.
    df : pandas DataFrame
        dataframe containing emissions data.
   Methods
    ----------
    __init__(self)
    add_data(self, rdate, states=['md'], download=False, verbose=True):
    load(self, efile, verbose=True):
    retrieve(self, rdate, state, download=True):

    match_column(self, varname):
    get_var(self, varname, loc=None, daterange=None, unitid=-99, verbose=True):
    retrieve(self, rdate, state, download=True):
    create_location_dictionary(self):
    rename(self, ccc, newname, rcolumn, verbose):
    """

    def __init__(self, key=None):
        self.efile = None
        self.url = "ftp://newftp.epa.gov/DmDnLoad/emissions/"
        self.apiurl = "https://api.epa.gov/FACT/1.0/"
        self.lb2kg = 0.453592  # number of kilograms per pound.
        self.info = "Data from continuous emission monitoring systems (CEMS)\n"
        self.info += self.url + "\n"

        self.df = pd.DataFrame()

        self.so2name = "SO2CEMReportedAdjustedSO2"
        self.namehash = {}  # if columns are renamed keeps track of original names.
        # Each facility may have more than one unit which is specified by the
        # unit id.
        self.key = key  # key to use for epa rest api request

        self.emit = Emissions(key)

    def __str__(self):
        return self.info

    def get_lookups(self):
        """
        Request to get lookups - descriptions of various codes.
        """
        getstr = "lookUps"
        rqq = self.apiurl + "emissions/" + getstr
        rqq += "?api_key=" + self.key
        data = requests.get(rqq)
        dstr = self.unpack(data)
        print(dstr)

        # According to lookups MODC values
        # 01 primary monitoring system
        # 02 backup monitoring system
        # 03 alternative monitoring system
        # 04 backup monitoring system

        # 06 average hour before/hour after
        # 07 average hourly

        # 21 negative value replaced with 0.
        # 08 90th percentile value in Lookback Period
        # 09 95th precentile value in Lookback Period
        # etc.

        # it looks like values between 1-4 ok
        # 6-7 probably ok
        # higher values should be flagged.

    def load_emissions(self, ifile):
        if os.path.isfile(ifile):
            df = pd.read_csv(ifile)
        self.df = df

    def unpack(self, response, deep=100):
        print("Status Code", response.status_code)
        jobject = response.json()
        dstr = unpack_response(jobject)
        return dstr

    def add_data(self, rdate, area, states=["md"], verbose=True, download=False):
        # 1. get list of oris codes within the area of interest
        # class FacilitiesData for this
        fac = FacilitiesData(key=self.key)
        llcrnr = (area[0], area[1])
        urcrnr = (area[2], area[3])
        orislist = fac.oris_by_area(llcrnr, urcrnr)
        datelist = get_datelist(rdate)
        print("ORIS to retrieve ", orislist)
        print("DATES ", datelist)
        # 2. get list of monitoring location ids for each oris code
        # FacilitiesData also provides this.
        for oris in orislist:
            units = fac.get_units(oris)
            print("Units to retrieve ", str(oris), units)
            for mid in units:
                plan = MonitoringPlan(oris, mid, self.key)
                for ndate in datelist:
                    # 3. get stack heights for each monitoring location from
                    #    class MonitoringPlan
                    mhash = plan.get(ndate)
                    if not mhash:
                        stackht = None
                    else:
                        stackht = mhash[0]["stackht"]
                    # 4. Call to the Emissions class to add each monitoring location
                    #    to the dataframe.
                    quarter = findquarter(ndate)
                    status = self.emit.add(
                        oris, mid, ndate.year, quarter, stackht=stackht, verbose=False
                    )
                    rstr = ""
                    ustr = ""
                    if status != 200:
                        if status == -99:
                            rstr = "NO SO2 \n"
                        else:
                            rstr = "Failed \n"
                        rstr += datetime.datetime.now().strftime("%Y %d %m %H:%M")
                        rstr += " Oris " + str(oris)
                        rstr += " Mid " + str(mid)
                        rstr += " Qrtr " + str(quarter)
                        rstr += "\n"
                    else:
                        ustr = "Loaded \n"
                        ustr += datetime.datetime.now().strftime("%Y %d %m %H:%M")
                        ustr += " Oris " + str(oris)
                        ustr += " Mid " + str(mid)
                        ustr += " Qrtr " + str(quarter)
                        ustr += "\n"
                    with open("log.txt", "a") as fid:
                        fid.write(rstr)
                        fid.write(ustr)

    def get_so2(self):
        self.df = emit.get_so2()
        return self.df

    def match_column(self, varname):
        """varname is list of strings.
           returns column name which contains all the strings.
        """
        columns = list(self.df.columns.values)
        cmatch = None
        for ccc in columns:
            # print('-----'  + ccc + '------')
            # print( temp[ccc].unique())
            match = 0
            for vstr in varname:
                if vstr.lower() in ccc.lower():
                    match += 1
            if match == len(varname):
                cmatch = ccc
        return cmatch

    def cemspivot(
        self, varname, daterange=None, unitid=False, stackht=False, verbose=True
    ):
        """
        Parameters
        ----------
        varname: string
            name of column in the cems dataframe
        daterange: list of two datetime objects
            define a date range
        unitid: boolean.
                 If True and unit id columns exist then these will be kept as
                 separate columns in the pivot table.
        verbose: boolean
                 if true print out extra information.
        stackht: boolean
                 NOT IMPLEMENTED YET. if true stack height is in header column.
        Returns: pandas DataFrame object
            returns dataframe with rows time. Columns are (oris,
            unit_id).
            If no unit_id in the file then columns are just oris.
            if unitid flag set to False then sums over unit_id's that belong to
             an oris. Values are from the column specified by the
             varname input.
        """
        from .obs_util import timefilter

        # stackht = False  # option not tested.
        temp = self.df.copy()
        if daterange:
            temp = timefilter(temp, daterange)
        # if stackht:
        #    stack_df = read_stack_height(verbose=verbose)
        #    olist = temp['oris'].unique()
        #    stack_df = stack_df[stack_df['oris'].isin(olist)]
        #    stack_df = max_stackht(stack_df)
        #    temp = temp.merge(stack_df, left_on=['oris'],
        #                      right_on=['oris'], how='left')
        if "unitid" in temp.columns.values and unitid:
            # if temp['unit_id'].unique():
            #    if verbose:
            #        print('UNIT IDs ', temp['unit_id'].unique())
            cols = ["oris", "unitid", "stackht"]
            # if stackht:
            #    cols.append('stackht')
        else:
            cols = ["oris", "stackht"]
            # if stackht:
            #    cols.append('max_stackht')

        # create pandas frame with index datetime and columns for value for
        # each unit_id,orispl
        pivot = pd.pivot_table(
            temp, values=varname, index=["time"], columns=cols, aggfunc=np.sum
        )
        # print('PIVOT ----------')
        # print(pivot[0:20])
        return pivot

    def get_var(self, varname, orisp=None, daterange=None, unitid=-99, verbose=True):
        """
           returns time series with variable indicated by varname.
           returns data frame where rows are date and columns are the
           values of cmatch for each fac_id.

           routine looks for column which contains all strings in varname.
           Currently not case sensitive.

           loc and ORISPL CODES.
           unitid is a unit_id

           if a particular unitid is specified then will return values for that
            unit.
        Parameters
        ----------
        varname : string or iteratable of strings
            varname may be string or list of strings.
        loc : type
            Description of parameter `loc`.
        daterange : type
            Description of parameter `daterange`.

        Returns
        -------
        type
            Description of returned object.
        """
        if unitid == -99:
            ui = False
        temp = self.cemspivot(varname, daterange, unitid=ui)
        if not ui:
            returnval = temp[orisp]
        else:
            returnval = temp[orisp, unitid]
        return returnval

    def retrieve(self, rdate, state, download=True, verbose=False):
        """Short summary.

        Parameters
        ----------
        rdate : datetime object
             Uses year and month. Day and hour are not used.
        state : string
            state abbreviation to retrieve data for
        download : boolean
            set to True to download
            if download FALSE then returns string with url of ftp
            if download TRUE then returns name of downloaded file

        Returns
        -------
        efile string
            if download FALSE then returns string with url of ftp
            if download TRUE then returns name of downloaded file
        """
        # import requests
        # TO DO: requests does not support ftp sites.
        efile = "empty"
        ftpsite = self.url
        ftpsite += "hourly/"
        ftpsite += "monthly/"
        ftpsite += rdate.strftime("%Y") + "/"
        print(ftpsite)
        print(rdate)
        print(state)
        fname = rdate.strftime("%Y") + state + rdate.strftime("%m") + ".zip"
        if not download:
            efile = ftpsite + fname
        if not os.path.isfile(fname):
            # print('retrieving ' + ftpsite + fname)
            # r = requests.get(ftpsite + fname)
            # open(efile, 'wb').write(r.content)
            # print('retrieved ' + ftpsite + fname)
            efile = ftpsite + fname
            print("WARNING: Downloading file not supported at this time")
            print("you may download manually using the following address")
            print(efile)
        else:
            print("file exists " + fname)
            efile = fname
        self.info += "File retrieved :" + efile + "\n"
        return efile

    def create_location_dictionary(self, verbose=False):
        """
        returns dictionary withe key oris and value  (latitude,
        longitude) tuple
        """
        if "latitude" in list(self.df.columns.values):
            dftemp = self.df.copy()
            pairs = zip(dftemp["oris"], zip(dftemp["latitude"], dftemp["longitude"]))
            pairs = list(set(pairs))
            lhash = dict(pairs)  # key is facility id and value is name.
            if verbose:
                print(lhash)
            return lhash
        else:
            return False

    def create_name_dictionary(self, verbose=False):
        """
        returns dictionary withe key oris and value facility name
        """
        if "latitude" in list(self.df.columns.values):
            dftemp = self.df.copy()
            pairs = zip(dftemp["oris"], dftemp["facility_name"])
            pairs = list(set(pairs))
            lhash = dict(pairs)  # key is facility id and value is name.
            if verbose:
                print(lhash)
            return lhash
        else:
            return False


def columns_rename(self, columns, verbose=False):
    """
    Maps columns with one name to a standard name
    Parameters:
    ----------
    columns: list of strings

    Returns:
    --------
    rcolumn: list of strings
    """
    rcolumn = []
    for ccc in columns:
        if "facility" in ccc.lower() and "name" in ccc.lower():
            rcolumn = self.rename(ccc, "facility_name", rcolumn, verbose)
        elif "oris" in ccc.lower():
            rcolumn = self.rename(ccc, "oris", rcolumn, verbose)
        elif "facility" in ccc.lower() and "id" in ccc.lower():
            rcolumn = self.rename(ccc, "fac_id", rcolumn, verbose)
        elif (
            "so2" in ccc.lower()
            and ("lbs" in ccc.lower() or "pounds" in ccc.lower())
            and ("rate" not in ccc.lower())
        ):
            rcolumn = self.rename(ccc, "so2_lbs", rcolumn, verbose)
        elif (
            "nox" in ccc.lower()
            and ("lbs" in ccc.lower() or "pounds" in ccc.lower())
            and ("rate" not in ccc.lower())
        ):
            rcolumn = self.rename(ccc, "nox_lbs", rcolumn, verbose)
        elif "co2" in ccc.lower() and (
            "short" in ccc.lower() and "tons" in ccc.lower()
        ):
            rcolumn = self.rename(ccc, "co2_short_tons", rcolumn, verbose)
        elif "date" in ccc.lower():
            rcolumn = self.rename(ccc, "date", rcolumn, verbose)
        elif "hour" in ccc.lower():
            rcolumn = self.rename(ccc, "hour", rcolumn, verbose)
        elif "lat" in ccc.lower():
            rcolumn = self.rename(ccc, "latitude", rcolumn, verbose)
        elif "lon" in ccc.lower():
            rcolumn = self.rename(ccc, "longitude", rcolumn, verbose)
        elif "state" in ccc.lower():
            rcolumn = self.rename(ccc, "state_name", rcolumn, verbose)
        else:
            rcolumn.append(ccc.strip().lower())
    return rcolumn


def rename(self, ccc, newname, rcolumn, verbose):
    """
    keeps track of original and new column names in the namehash attribute
    Parameters:
    ----------
    ccc: str
    newname: str
    rcolumn: list of str
    verbose: boolean
    Returns
    ------
    rcolumn: list of str
    """
    # dictionary with key as the newname and value as the original name
    self.namehash[newname] = ccc
    rcolumn.append(newname)
    if verbose:
        print(ccc + " to " + newname)
    return rcolumn
