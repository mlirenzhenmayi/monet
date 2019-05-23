from __future__ import print_function
import os
import datetime
import sys
import pandas as pd
import numpy as np
import requests
import pytz
# import json
import seaborn as sns
import monet.obs.obs_util as obs_util

"""
NAME: cems_api.py
PGRMMER: Alice Crawford   ORG: ARL
This code written at the NOAA air resources laboratory
Python 3
#################################################################
The key and url for the epa api should be stored in a file called
.epaapirc in the $HOME directory.
The contents should be

key: apikey
url: https://api.epa.gov/FACT/1.0/

TO DO
-----
Date is in local time (not daylight savings)
Need to convert to UTC.

Classes:
----------
Emissions
FacilitiesData
MonitoringPlan
CEMS

Functions:
----------

addquarter
get_datelist
findquarter
sendrequest
getkey

"""
def get_filename(fname, prompt):
    if fname:
        done=False
        while not done:
            if os.path.isfile(fname):
               done = True
            elif prompt==True:
               istr = '\n' +  fname + ' is not a valid name for Facilities Data \n'
               istr += 'Please enter a new filename \n'
               istr += 'enter None to load from the api \n'
               istr += 'enter x to exit program \n'
               fname=input(istr)
               #print('checking ' + fname)
               if fname=='x': sys.exit()
               if fname.lower()=='none': 
                  fname=None
                  done=True
            else:
               fname=None
               done=True 
    return fname


def get_timezone_offset(latitude, longitude):
    """
    uses geonames API 
    must store username in the $HOME/.epaapirc file
    geousername: username
    """
    username=getkey()
    print(username)
    username = username['geousername']
    url='http://api.geonames.org/timezoneJSON?lat='
    request = url + str(latitude) 
    request += '&lng=' 
    request += str(longitude)
    request += '&username='
    request += username
    try:
        data = requests.get(request)
    except BaseException:
        data = -99
 
    jobject = data.json()
    print(jobject)
    print(data)
    #raw offset should give standard time offset.
    if data == -99:
        return 0
    else:
        offset = jobject['rawOffset']
        return offset

def getkey():
    """
    key and url should be stored in $HOME/.epaapirc
    """
    dhash = {}
    homedir = os.environ["HOME"]
    fname = "/.epaapirc"
    if os.path.isfile(homedir + fname):
        with open(homedir + fname) as fid:
            lines = fid.readlines()
        for temp in lines:
            temp = temp.split(" ")
            dhash[temp[0].strip().replace(":", "")] = temp[1].strip()
        return dhash
    else:
        dhash["key"] = None
        dhash["url"] = None
        dhash["geousername"] = None
        return dhash


def sendrequest(rqq, key=None, url=None):
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
    if not key or not url:
        keyhash = getkey()
        apiurl = keyhash["url"]
        key = keyhash["key"]
    if key:
        # apiurl = "https://api.epa.gov/FACT/1.0/"
        rqq = apiurl + rqq + "?api_key=" + key
        print("Request: ", rqq)
        data = requests.get(rqq)
        print("Status Code", data.status_code)
        if data.status_code==429:
           print('Too many requests Please Wait before trying again.')
           sys.exit()
        return data



def get_lookups():
    """
        Request to get lookups - descriptions of various codes.
        """
    getstr = "emissions/lookUps"
    # rqq = self.apiurl + "emissions/" + getstr
    # rqq += "?api_key=" + self.key
    data = sendrequest(getstr)
    dstr = unpack_response(data)
    return dstr

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


def keepcols(df, keeplist):
    tcols = df.columns.values
    klist=[]
    for ttt in keeplist:
        if ttt not in tcols:
            print("NOT IN ", ttt)
            print('Available', tcols)
        else:
            klist.append(ttt)
    tempdf = df[klist]
    return tempdf


def get_so2(df):
    """
    drop columns that are not in keep.
    """
    keep = [
        "DateHour",
        "time",
        "OperatingTime",
        "HourLoad",
        #"u so2_lbs",
        "so2_lbs",
        "AdjustedFlow",
        "UnadjustedFlow",
        "FlowMODC",
        "SO2MODC",
        "unit",
        "stackht",
        "oris",
        "latitude",
        "longitude",
    ]
    return keepcols(df, keep)


class Emissions:
    """
    class that represents data returned by emissions/hourlydata call to the restapi.
    Attributes
    self.df : DataFrame

    Methods
    __init__
    add

    see
    https://www.epa.gov/airmarkets/field-audit-checklist-tool-fact-field-references#EMISSION
     
    class that represents data returned by facilities call to the restapi.
    # NOTES
    # BAF - bias adjustment factor
    # MEC - maximum expected concentraiton
    # MPF - maximum potential stack gas flow rate
    # monitoring plan specified monitor range.
    # FlowPMA % of time flow monitoring system available.

    # SO2CEMReportedAdjustedSO2 - average adjusted so2 concentration
    # SO2CEMReportedSO2MassRate - average adjusted so2 rate (lbs/hr)

    # AdjustedFlow - average volumetric flow rate for the hour. adjusted for
    # bias.

    # It looks like MassRate is calculated from concentration of SO2 and flow
    # rate. So flow rate should be rate of all gasses coming out of stack. 

    """

    def __init__(self):
        self.df = pd.DataFrame()
        self.orislist = []
        self.unithash = {}
        #self.so2name = "SO2CEMReportedAdjustedSO2"
        self.so2name = "SO2CEMReportedSO2MassRate"

        self.so2nameB = "UnadjustedSO2"

    def add(
            self,
            oris,
            locationID,
            year,
            quarter,
            ifile="efile.txt",
            verbose=False,
            # data2add=None,
            # stackht=None,
            # facname=None,
            logfile="warnings.emit.txt",
    ):
        """
        oris : int
        locationID : str
        year : int
        quarter : int
        ifile : str
        data2add : list of tuples (str, value)
                   str is name of column. value to add to column.

        """

        if oris not in self.orislist:
            self.orislist.append(oris)
        if oris not in self.unithash.keys():
            self.unithash[oris] = []
        self.unithash[oris].append(locationID)
        with open(logfile, "w") as fid:
            dnow = datetime.datetime.now()
            fid.write(dnow.strftime("%Y %m %d %H:%M/n"))
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
        getstr = "/".join([estr, str(oris), locationID,
                           str(year), str(quarter)])

        # returns csv file rather than json object.
        data = sendrequest(getstr)

        if data.status_code != 200:
            return data.status_code

        iii = 0
        cols = []
        for line in data.iter_lines(decode_unicode=True):

            # 1. Process First line
            if iii == 0:
                tcols = line.split(",")
                # add columns for unit id and oris code
                tcols.append("unit")
                tcols.append("oris")
                # add columns for other info (stack height, latitude etc).
                # for edata in data2add:
                #    tcols.append(edata[0])
                # 1a write column headers to a file.
                verbose=True
                if verbose:
                    with open("headers.txt", "w") as fid:
                        for val in tcols:
                            fid.write(val + "\n")
                    # print('press a key to continue ')
                    # input()
                # 1b check to see if desired emission variable is in the file.
                if self.so2name not in tcols:
                    with open(logfile, "a") as fid:
                        rstr = "ORIS " + str(oris)
                        rstr += " mid " + str(locationID) + "\n"
                        rstr += "NO adjusted SO2 data \n"
                        if self.so2nameB not in tcols:
                            rstr += "NO SO2 data \n"
                        rstr += "------------------------\n"
                        fid.write(rstr)
                    print("--------------------------------------")
                    print("ORIS " + str(oris))
                    print("UNIT " + str(locationID) + " no SO2 data")
                    print("--------------------------------------")
                    return -999
                else:
                    cols = tcols
            # 2. Process rest of lines
            else:
                lt = line.split(",")
                # add input info to line.
                lt.append(locationID)
                lt.append(int(oris))
                # for edata in data2add:
                #    lt.append(edata[1])
                tra.append(lt)
            iii += 1
            # with open(efile, "a") as fid:
            #    fid.write(line)
        # ----------------------------------------------------
        df = pd.DataFrame(tra, columns=cols)
        # print(df[0:10])
        df.apply(pd.to_numeric, errors="ignore")
        df = self.manage_date(df)
        df = self.convert_cols(df)
        tempdf = get_so2(df)
        if self.df.empty:
            self.df = df
        else:
            self.df = self.df.append(df)
        tempdf.to_csv(efile)
        return data.status_code

    def merg_facilities(self, dfac):
        dfnew = pd.merge(
            self.df,
            dfac,
            how="left",
            left_on=["oris", "unit"],
            right_on=["oris", "unit"],
        )
        return dfnew

    def convert_cols(self, df):
        """
        All columns are read in as strings and must be converted to the
        appropriate units. NaNs or empty values may be present in the columns.

        OperatingTime : fraction of the clock hour during which the unit
                        combusted any fuel. If unit, stack or pipe did not
                        operate report 0.00.
        """

        def toint(xxx):
            try:
                rt = int(xxx)
            except BaseException:
                rt = xxx
            return rt

        def simpletofloat(xxx):
            try:
                rt = float(xxx)
            except BaseException:
                rt = -999
            return rt

        # calculate lbs of so2 by multiplying rate by operating time.
        # checked this with FACTS
        def getmass(optime, cname):
            if float(optime)==0:
                rval = 0
            else:
                try:
                    rval = float(cname) * float(optime)
                except BaseException:
                    rval = -999
                    #rval = 0
            return rval



        # map OperatingTime to a float
        df["OperatingTime"] = df["OperatingTime"].map(simpletofloat)
        # map Adjusted Flow to a float
        df["AdjustedFlow"] = df["AdjustedFlow"].map(simpletofloat)
        #df["oris"] = df["oris"].map(toint)
        df["oris"] = df.apply(lambda row: toint(row['oris']), axis=1)
        # map SO2 data to a float
        # if operating time is zero then map to 0 (it is '' in file)
        optime = "OperatingTime"
        cname = "UnadjustedSO2"
        cname = self.so2name
        df["so2_lbs"] = df.apply(
            lambda row: getmass(
                row[optime],
                row[cname]),
                axis=1)

        # temp is values that are not valid
        temp = df[df["so2_lbs"].isin([-999])]
        temp = temp[temp["OperatingTime"] > 0]
        print("Values that cannot be converted to float")
        print(temp[cname].unique())
        print("MODC ", temp["SO2MODC"].unique())
        ky = "MATSSstartupshutdownflat"
        if ky in temp.keys():
            print("MATSSstartupshutdownflat",
                  temp["MATSStartupShutdownFlag"].unique())
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

           # also need to change to UTC.

           # time is local standard time (never daylight savings)
        """
        # Using the %I for the hour field and %p for AM/Pm converts time
        # correctly.
        def newdate(xxx):
            fmt = "%m/%d/%Y %I:%M:%S %p"
            try:
                rdt = datetime.datetime.strptime(xxx["DateHour"], fmt)
            except BaseException:
                print("PROBLEM DATE :", xxx["DateHour"], ":")
                rdt = datetime.datetime(1000, 1, 1, 0)
            return rdt

        df["time local"] = df.apply(newdate, axis=1)
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
        for unit in df["unit"].unique():
            temp = temp1[temp1["unit"] == unit]
            temp = temp[temp["SO2MODC"].isin(["01", "02", "03", "04"])]
            plt.plot(temp["date"], temp["so2_lbs"], label=str(unit))
            print("UNIT", str(unit))
            print(temp["SO2MODC"].unique())
        for unit in df["unit"].unique():
            temp = temp1[temp1["unit"] == unit]
            temp = temp[temp["SO2MODC"].isin(
                ["01", "02", "03", "04"]) == False]
            plt.plot(temp["date"], temp["so2_lbs"], label="bad " + str(unit))
            print("UNIT", str(unit))
            print(temp["SO2MODC"].unique())
        ax = plt.gca()
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels)
        plt.show()
        for unit in df["unit"].unique():
            temp = temp1[temp1["unit"] == unit]
            print("BAF", temp["FlowBAF"].unique())
            print("MODC", temp["FlowMODC"].unique())
            print("PMA", temp["FlowPMA"].unique())
            plt.plot(temp["date"], temp["AdjustedFlow"], label=str(unit))
        plt.show()


class MonitoringPlan:
    """ 
    Stack height is converted to meters.

    """

    def __init__(self, oris, mid, date):
        self.df = pd.DataFrame()
        self.oris = oris  # oris code of facility
        self.mid = mid    # monitoring location id.
        self.date = date  # date
        self.getstr = self.create_getstr()

    def save(self, fname):
        self.df.to_csv(fname) 

    def printall(self):
        getstr = self.create_getstr()
        data = sendrequest(getstr)
        jobject = data.json()
        rstr = getstr + '\n'
        rstr += unpack_response(jobject)
        return rstr

    def create_getstr(self):
        oris = self.oris
        mid = self.mid
        dstr = self.date.strftime("%Y-%m-%d")
        mstr = "monitoringplan"
        getstr = "/".join([mstr, str(oris), str(mid), dstr])
        return getstr 


    def get(self):
        """
        Request to get monitoring plans for oris code and locationID.
        locationIDs for an oris code can be found in

        The monitoring plan has locationAttributes which
        include the stackHeight, crossAreaExit, crossAreaFlow.

        It also includes monitoringSystems which includes
        ststeymTypeDescription (such as So2 Concentration)

        QuarterlySummaries gives so2Mass each quarter.
        """
        #oris = self.oris
        #mid = self.mid
        #dstr = date.strftime("%Y-%m-%d")
        #mstr = "monitoringplan"
        #getstr = "/".join([mstr, str(oris), str(mid), dstr])
        data = sendrequest(self.getstr)
        if data.status_code != 200:
            return None
        jobject = data.json()
        dlist = self.unpack(jobject["data"])
        return dlist

    # @staticmethod
    def unpack(self, ihash):
        """
        dhash :
        Returns:

        Information for one oris code and monitoring location.
        columns
        stackname, unit, stackheight, crossAreaExit,
        crossAreaFlow, locID, isunit
        """
        ft2meters = 0.3048
        dlist = []
        # print(ihash.keys())
        stackname = ihash["unitStackName"]
        for unithash in ihash["monitoringLocations"]:
            dhash = {}
            dhash["unit"] = self.mid
            dhash["name"] = unithash["name"]
            dhash["isunit"] = unithash["isUnit"]
            for att in unithash["locationAttributes"]:
                # dhash = {}
                dhash["stackname"] = stackname
                # dhash["unit"] = self.mid
                dhash["stackht"] = att["stackHeight"]  * 0.3048 # int
                dhash["stackht unit"] = 'm' # int
                dhash["crossAreaExit"] = att["crossAreaExit"]  # int
                dhash["crossAreaFlow"] = att["crossAreaFlow"]  # int
                dhash["locID"] = att["locId"]
                # dhash["isunit"] = att["isUnit"]
                # dlist.append(dhash)
            for method in unithash["monitoringMethods"]:
                if method["parameterCode"] == "SO2":
                    dhash["parameterCode"] = "SO2"
                    dhash["methodCode"] = method["methodCode"]
                    dhash["subDataCode"] = method["subDataCode"]
                    dhash["parameterCodeDesc"] = method["parameterCodeDesc"]
            for method in unithash["emissionsFormulas"]:
                if method["parameterCode"] == "SO2":
                    elist = [
                        "formulaId",
                        "parameterCode",
                        "equationCode",
                        "formulaEquation",
                        "equationCodeDesc",
                    ]
                    for val in elist:
                        dhash[val] = method[val]

            dlist.append(dhash)
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
# this is complicated because entires for multiple types of equipment.

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


class EpaApiObject(object):
    
    def __init__(self, fname=None, prompt=False):
        self.df = pd.DataFrame()
        self.fname = get_filename(fname, prompt)
        self.getstr = self.create_getstr()

    def set_filename(self, fname):
        self.fname = fname    

    def load(self):
        df = pd.read_csv(self.fname, index_col=[0])
        return df

    def save(self):
        """
        save to a csv file.
        """
        self.df.to_csv(self.fname)
        self.fname = fname

    def create_getstr():
        return 'placeholder'

    def get(self):
        data = sendrequest(self.getstr)
        jobject = data.json()
        self.df = self.unpack(jobject)




class FacilitiesData(EpaApiObject):
    """
    class that represents data returned by facilities call to the restapi.

    Attributes:
        self.fname : filename for reading and writing df to csv file.
        self.df  : dataframe
         columns are
         begin time,
         end time,
         isunit (boolean),
         latitude,
         longitude,
         facility_name,
         oris,
         unit

    Methods:
        __init__
        printall : returns a string with the unpacked data.
        get : sends request to the restapi and calls unpack.
        oris_by_area : returns list of oris codes in an area
        get_units : returns a list of units for an oris code

        set_filename : set filename to save and load from.
        load : load datafraem from csv file
        save : save dateframe to csv file
        get  : request facilities information from api
        unpack : process the data sent back from the api
                 and put relevant info in a dataframe.

    """

    def __init__(self, fname=None, prompt=True):
        self.df = pd.DataFrame()
        self.fname = get_filename(fname, prompt)
        if self.fname:
           self.df = self.load()
        else:
           self.get() 
        # self.oris = oris   #oris code of facility
        # self.mid = mid     #monitoring location id.


    def set_filename(self, fname):
        self.fname = fname
       
    def load(self):
        df = pd.read_csv(self.fname, index_col=[0])
        return df
 
    def save(self, fname):
        """
        save to a csv file.
        """
        self.df.to_csv(fname)
        self.fname = fname

    def __str__(self):
        cols = self.df.columns
        rstr = ', '.join(cols)
        return rstr

    def printall(self):
        getstr = "facilities"
        data = sendrequest(getstr)
        jobject = data.json()
        rstr = unpack_response(jobject)
        return rstr

    def get(self):
        """
        Request to get facilities information
        """
        getstr = "facilities"
        data = sendrequest(getstr)
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
        for a particular oris code.
        """
        oris = int(oris)
        # if self.df.empty:
        #    self.facdata()
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
        # dlist is a list of dictionaries.
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
            ahash["facility_name"] = val["name"]
            ahash["latitude"] = val["geographicLocation"]["latitude"]
            ahash["longitude"] = val["geographicLocation"]["longitude"]
            #ahash['time_offset'] = get_timezone_offset(ahash['latitude'],
            #                       ahash['longitude'])
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

    """

    def __init__(self):
        self.efile = None
        self.lb2kg = 0.453592  # number of kilograms per pound.
        self.info = "Data from continuous emission monitoring systems (CEMS)\n"
        self.df = pd.DataFrame()
        self.so2name = "SO2CEMReportedAdjustedSO2"
        # Each facility may have more than one unit which is specified by the
        # unit id.
        self.emit = Emissions()
        self.orislist = []

        #self.filehash = {}
        #self.filehash{'facilities'} = 'Fac.csv'
        #self.filehash{'monitoring'} = 'Mon.csv'

    def add_facilities_file(self, fname):
        self.filehash['facilities'] = fname

    def add_data(self, rdate, area, verbose=True):
        """
        INPUTS:
        rdate :  either datetime object or tuple of two datetime objects.
        area  : list of 4 floats. (lat, lon, lat, lon)
        verbose : boolean

        RETURNS:
        emitdf : pandas DataFrame with SO2 emission information.

        # 1. get list of oris codes within the area of interest
        # 2. get list of monitoring location ids for each oris code
        # 3. each unit has a monitoring plan.
        # 4. get stack heights for each monitoring location from
        #    class MonitoringPlan
        # 5. Call to the Emissions class to add each monitoring location
        #    to the dataframe.


        TODO - MonitoringPlan contains quarterly summaries of mass and operating
               time. May be able to use those

        TODO - to generalize to emissions besides SO2. Modify get_so2 routine.

        TODO - what is the flow rate?

        

        """
        # 1. get list of oris codes within the area of interest
        # class FacilitiesData for this
        fac = FacilitiesData()
        llcrnr = (area[0], area[1])
        urcrnr = (area[2], area[3])
        orislist = fac.oris_by_area(llcrnr, urcrnr)
        datelist = get_datelist(rdate)
        if verbose:
            print("ORIS to retrieve ", orislist)
        if verbose:
            print("DATES ", datelist)
        # 2. get list of monitoring location ids for each oris code
        # FacilitiesData also provides this.
        facdf = fac.df[fac.df["oris"].isin(orislist)]
        facdf = facdf.drop(["begin time", "end time"], axis=1)
        dflist = []
        for oris in orislist:
            units = fac.get_units(oris)
            if verbose:
                print("Units to retrieve ", str(oris), units)
            # 3. each unit has a monitoring plan.
            for mid in units:
                # 4. get stack heights for each monitoring location from
                #    class
                # although the date is included for the monitoring plan request,
                # the information returned is the same most of the time
                # (possibly unless the monitoring plan changes during the time
                # of interst).
                # to reduce number of requests, the monitoring plan is only
                # requested for the first date in the list.
                plan = MonitoringPlan(oris, mid, datelist[0])
                mhash = plan.get()
                for ndate in datelist:
                    if mhash: 
                        if len(mhash) > 1:
                            print(
                                "CEMS class WARNING: more than one \
                                  Monitoring location for this unit\n"
                            )
                            for val in mhash:
                                print("unit " + val["name"] + " oris " + str(oris))
                            sys.exit()
                        else:
                            mhash = mhash[0]
                            stackht = float(mhash["stackht"])
                    else:
                        stackht = None
                    dflist.append((oris, mid, stackht))
                    # 5. Call to the Emissions class to add each monitoring location
                    #    to the dataframe.
                    quarter = findquarter(ndate)
                    status = self.emit.add(
                        oris,
                        mid,
                        ndate.year,
                        quarter,
                        # facname=facname,
                        # stackht=stackht,
                        verbose=False,
                    )
                    if status == 200:
                        self.orislist.append((oris, mid))
                    write_status_message(status, oris, mid, quarter, "log.txt")
        # merge stack height data into the facilities information data frame.
        tempdf = pd.DataFrame(dflist, columns=["oris", "unit", "stackht"])
        facdf = pd.merge(
            tempdf,
            facdf,
            how="left",
            left_on=["oris", "unit"],
            right_on=["oris", "unit"],
        )
        # drop un-needed columns from the emissions DataFrame
        print('CEMS API ZZZZ')
        emitdf = get_so2(self.emit.df)
        # merge data from the facilties DataFrame into the Emissions DataFrame
        emitdf = pd.merge(
            emitdf,
            facdf,
            how="left",
            left_on=["oris", "unit"],
            right_on=["oris", "unit"],
        )
        self.df = emitdf
        return emitdf


def write_status_message(status, oris, mid, quarter, logfile):
    rstr = ""
    # ustr = ""
    if status != 200:
        if status == -99:
            rstr = "NO SO2 \n"
        else:
            rstr = "Failed \n"
        # rstr += datetime.datetime.now().strftime("%Y %d %m %H:%M")
        # rstr += " Oris " + str(oris)
        # rstr += " Mid " + str(mid)
        # rstr += " Qrtr " + str(quarter)
        # rstr += "\n"
    else:
        rstr = "Loaded \n"
        rstr += datetime.datetime.now().strftime("%Y %d %m %H:%M")
    rstr += " Oris " + str(oris)
    rstr += " Mid " + str(mid)
    rstr += " Qrtr " + str(quarter)
    rstr += "\n"
    with open(logfile, "a") as fid:
        fid.write(rstr)
        # fid.write(ustr)


def match_column(df, varname):
    """varname is list of strings.
       returns column name which contains all the strings.
    """
    columns = list(df.columns.values)
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


def latlon2str(lat, lon):
    latstr = "{:.4}".format(lat)
    lonstr = "{:.4}".format(lon)
    return (latstr, lonstr)


def cemspivot(df, varname, cols=['oris','stackht'], daterange=None,  verbose=True):
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
        returns dataframe with rows time. Columns are (oris, stackht)
        If no unit_id in the file then columns are just oris.
        if unitid flag set to False then sums over unit_id's that belong to
        an oris. Values are from the column specified by the
        varname input.
    """
    from .obs_util import timefilter

    temp = df.copy()
    if daterange:
        temp = timefilter(temp, daterange)
    #if "unitid" in temp.columns.values and unitid:
        # if temp['unit_id'].unique():
        #    if verbose:
        #        print('UNIT IDs ', temp['unit_id'].unique())
    #    cols = ["oris", "unitid", "stackht"]
        # if stackht:
        #    cols.append('stackht')
    #else:
    #    cols = ["oris", "stackht", "latlon"]
        # if stackht:
        #    cols.append('max_stackht')
    #temp["latlon"] = temp.apply(
    #    lambda row: latlon2str(row["latitude"], row["longitude"]), axis=1
    #)
    # create pandas frame with index datetime and columns for value for
    # each unit_id,orispl

    #cols = ['oris','stackht']
    pivot = pd.pivot_table(
        temp, values=varname, index=["time"], columns=cols, aggfunc=np.sum
    )
    # print('PIVOT ----------')
    # print(pivot[0:20])
    return pivot


def get_var(df, varname, orisp=None, daterange=None, unitid=-99, verbose=True):
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
    temp = cemspivot(df, varname, daterange, unitid=ui)
    if not ui:
        returnval = temp[orisp]
    else:
        returnval = temp[orisp, unitid]
    return returnval
