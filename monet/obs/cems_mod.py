import datetime
import os
import sys
import numpy as np
import pandas as pd
from monet.obs.cems_api import FacilitiesData
from monet.obs.cems_api import get_monitoring_plan
from monet.obs.cems_api import get_datelist

"""
NAME: cems_mod.py
PGRMMER: Alice Crawford   ORG: ARL
This code written at the NOAA air resources laboratory
Python 3
#################################################################
"""


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


def read_stack_height(verbose=False, testing=False):
    """
    reads file with information on stack heights and diameters and returns a
    dataframe.
    Parameters
    ----------
    verbose: boolean
             if true prints out header information in file.
    testing: boolean
             if true returns dataframe with more columns
    Returns
    -------
    df2: pandas dataframe
         dataframe which contains columns which have stack height and diameter
         for each orispl code and stackid.

    TO DO: CEMS data contains a unit_id but this doesn't seem to correspond to
    the ids availble in the ptinv file. Not clear how to match individual units
    with the same orispl code.
    """
    pd.options.mode.chained_assignment = None
    # This file was obtained from Daniel Tong and Youhua Tang 9/13/2018
    # stack height is in feet in the file.
    basedir = os.path.abspath(os.path.dirname(__file__))[:-3]
    fn = "ptinv_ptipm_cap2005nei_20jun2007_v0_orl.txt"
    fname = os.path.join(basedir, "data", fn)

    df = pd.read_csv(fname, comment="#")
    orispl = "ORIS_FACILITY_CODE"
    # drop rows which have nan in the ORISPL code.
    df.dropna(inplace=True, axis=0, subset=["ORIS_FACILITY_CODE"])
    # df[orispl].fillna(-999, inplace=True)
    df[orispl] = df[orispl].astype(int)

    if verbose:
        print("Data available in ptinv file")
        print(df.columns.values)
        print("----------------------------")
    if testing:  # for testing purposes output all the id codes.
        df2 = df[
            [
                "STACKID",
                "PLANTID",
                "POINTID",
                "FIPS",
                "ORIS_BOILER_ID",
                "STKHGT",
                "STKDIAM",
                orispl,
                "PLANT",
            ]
        ]
        df2.columns = [
            "stackid",
            "plantid",
            "pointid",
            "fips",
            "boiler",
            "stackht",
            "stackdiam",
            "oris",
            "plant",
        ]
    else:
        # May use stack diamter, temperature and velocity for plume rise.
        # match the oris_boiler_ID to unitid from the cems data.
        df2 = df[
            [
                orispl,
                "STACKID",
                "ORIS_BOILER_ID",
                "STKHGT",
                "STKDIAM",
                "STKTEMP",
                "STKVEL",
            ]
        ]
        df2.columns = [
            "oris",
            "stackid",
            "boilerid",
            "stackht",
            "stackdiam",
            "stacktemp",
            "stackvel",
        ]
    df2.drop_duplicates(inplace=True)
    df2 = df2[df2["oris"] != -999]
    # df2 = max_stackht(df2)
    # df2.drop(['stackht'], inplace=True)
    # df2.drop_duplicates(inplace=True)
    # print('done here')
    return df2


def getdegrees(degrees, minutes, seconds):
    return degrees + minutes / 60.0 + seconds / 3600.00


def addmonth(dt):
    month = dt.month + 1
    year = dt.year
    day = dt.day
    hour = dt.hour
    if month > 12:
        year = dt.year + 1
        month = month - 12
        if day == 31 and month in [4, 6, 9, 11]:
            day = 30
        if month == 2 and day in [29, 30, 31]:
            if year % 4 == 0:
                day = 29
            else:
                day = 28
    return datetime.datetime(year, month, day, hour)


def get_date_fmt(date, verbose=False):
    """Determines what format of the date is in.
    In some files year is first and others it is last.
    Parameters
    ----------
    date: str
          with format either YYYY-mm-DD or mm-DD-YYYY
    verbose: boolean
          if TRUE print extra information
    Rerturns
    --------
    fmt: str
        string which can be used with datetime object to give format of date
        string.
    """
    if verbose:
        print("Determining date format")
    if verbose:
        print(date)
    temp = date.split("-")
    if len(temp[0]) == 4:
        fmt = "%Y-%m-%d %H"
    else:
        fmt = "%m-%d-%Y %H"
    return fmt


class CEMSftp(object):
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

    def __init__(self):
        self.efile = None
        self.url = "ftp://newftp.epa.gov/DmDnLoad/emissions/"
        self.lb2kg = 0.453592  # number of kilograms per pound.
        self.info = "Data from continuous emission monitoring systems (CEMS)\n"
        self.info += self.url + "\n"
        self.df = pd.DataFrame()
        self.namehash = {}  # if columns are renamed keeps track of original names.
        self.orislist = []

        # Each facility may have more than one unit which is specified by the
        # unit id.

    def __str__(self):
        return self.info

    # def add_data(self, rdate, states=["md"], download=False, verbose=True):
    def add_data(self, rdate, alist, area=True, download=True, verbose=True):
        """
           gets the ftp url from the retrieve method and then
           loads the data from the ftp site using the load method.

        Parameters
        ----------
        rdate : single datetime object of list of datetime objects
               The first datetime object indicates the month and year of the
               first file to retrieve.
               The second datetime object indicates the month and year of the
               last file to retrieve.
        states : list of strings
             list of two letter state identifications.
        download : boolean
               if download=True then retrieve will download the files and load
               will read the downloaded files.
               if download=False then retrieve will return the url and load
               will read directly from ftp site.
        verbose : boolean
               if TRUE prints out additional information.
        Returns
        -------
        boolean True

        """
        ## To DO need to generate list of states from either list of oris codes
        ## or lat lon coordinates
        # md is 1552 (ok)
        # ms is 2049 (problem)
        self.fac = FacilitiesData()
        if area:
            llcrnr = (alist[0], alist[1])
            urcrnr = (alist[2], alist[3])
            orislist = self.fac.oris_by_area(llcrnr, urcrnr)
            states = self.fac.state_from_oris(orislist)
        else:
            orislist = alist
            states = self.fac.state_from_oris(orislist)
        self.orislist.extend(orislist)

        if isinstance(states, str):
            states = [states]
        if isinstance(rdate, list):
            r1 = rdate[0]
            r2 = rdate[1]
            rdatelist = [r1]
            done = False
            iii = 0
            while not done:
                r3 = addmonth(rdatelist[-1])
                if r3 <= r2:
                    rdatelist.append(r3)
                else:
                    done = True
                if iii > 100:
                    done = True
                iii += 1
        else:
            rdatelist = [rdate]
        for rd in rdatelist:
            print("getting data")
            print(rd)
            for st in states:
                url = self.retrieve(rd, st, download=download, verbose=verbose)
                self.load(url, verbose=verbose)
        self.df["SO2MODC"] = 2
        return self.df

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
            if "unitid" in ccc.lower():
                rcolumn = self.rename(ccc, "unit", rcolumn, verbose)
            elif "facility" in ccc.lower() and "name" in ccc.lower():
                rcolumn = self.rename(ccc, "facility_name", rcolumn, verbose)
            elif "op_time" in ccc.lower():
                rcolumn = self.rename(ccc, "OperatingTime", rcolumn, verbose)
            elif "orispl" in ccc.lower():
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

    def add_info(self, dftemp, datelist):
        if not self.orislist:
            orislist = dftemp["oris"].unique()
        else:
            orislist = self.orislist
            print("ORIS available in ftp download", dftemp["oris"].unique())
            dftemp = dftemp[dftemp["oris"].isin(orislist)]
        print("orislist to retrieve", orislist)
        facdf = self.fac.df[self.fac.df["oris"].isin(map(str, orislist))]
        dflist = []
        for oris in orislist:
            t1 = dftemp[dftemp["oris"] == oris]
            unitsA = t1["unit"].unique()
            unitsB = self.fac.get_units(oris)
            print("---------------------------------------")
            print("ORIS: ", oris)
            print("units in FacilitiesData", unitsB)
            print("units in ftp data", unitsA)
            print(datelist)
            print("---------------------------------------")
            for mid in unitsA:
                mrequest = None
                iii = 0
                for udate in datelist:
                    mrequest = self.fac.get_unit_request(oris, mid, udate)
                    if mrequest:
                        break
                if mrequest:
                    dflist = get_monitoring_plan(oris, mid, mrequest, udate, dflist)
        stackdf = pd.DataFrame(dflist, columns=["oris", "unit", "stackht"])
        facdf = facdf[["oris", "unit", "facility_name", "latitude", "longitude"]]
        facdf = facdf.drop_duplicates()
        facdf = pd.merge(
            stackdf,
            facdf,
            how="left",
            left_on=["oris", "unit"],
            right_on=["oris", "unit"],
        )
        # get facility name from the api.
        dftemp.drop(["facility_name"], inplace=True, axis=1)
        c1 = facdf.columns.values
        c2 = dftemp.columns.values
        jlist = [x for x in c1 if x in c2]
        # ftemp = facdf[['oris','latitude','longitude','unit','stackht']]
        # ftemp = ftemp[ftemp['oris']=='1571']
        # print(ftemp)
        # print('merging on', jlist)
        # print(dftemp.dtypes)
        # print('---')
        # print(facdf.dtypes)
        emitdf = pd.merge(dftemp, facdf, how="left", left_on=jlist, right_on=jlist)
        return emitdf

    def load(self, efile, verbose=True):
        """
        loads information found in efile into a pandas dataframe.
        Parameters
        ----------
        efile: string
             name of csv file to open or url of csv file.
        verbose: boolean
             if TRUE prints out information
        """

        # pandas read_csv can read either from a file or url.
        chash = {"ORISPL_CODE": str}
        dftemp = pd.read_csv(
            efile, sep=",", index_col=False, header=0, converters=chash
        )
        columns = list(dftemp.columns.values)
        columns = self.columns_rename(columns, verbose)
        dftemp.columns = columns
        print("zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")
        print("Loading from ftp " + efile)
        print(columns)
        print("zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")
        if verbose:
            print(columns)
        dfmt = get_date_fmt(dftemp["date"][0], verbose=verbose)

        # create column with datetime information
        # from column with month-day-year and column with hour.
        dftime = dftemp.apply(
            lambda x: pd.datetime.strptime(
                "{0} {1}".format(x["date"], x["hour"]), dfmt
            ),
            axis=1,
        )
        dftemp = pd.concat([dftime, dftemp], axis=1)
        dftemp.rename(columns={0: "time local"}, inplace=True)
        dftemp.drop(["date", "hour"], axis=1, inplace=True)

        # -------------Load supplmental data-----------------------
        # contains info on facility id, lat, lon, time offset from UTC.
        # allows transformation from local time to UTC.
        dftime = dftime.tolist()
        datelist = get_datelist([dftime[0], dftime[-1]])
        dftemp = self.add_info(dftemp, datelist)
        verbose = True
        if ["year"] in columns:
            dftemp.drop(["year"], axis=1, inplace=True)
        if self.df.empty:
            self.df = dftemp
            if verbose:
                print("Initializing pandas dataframe. Loading " + efile)
        else:
            self.df = self.df.append(dftemp)
            if verbose:
                print("Appending to pandas dataframe. Loading " + efile)
        # if verbose: print(dftemp[0:10])
        return dftemp
