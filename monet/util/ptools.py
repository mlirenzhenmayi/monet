# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import matplotlib.dates as mdates
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import datetime

"""
NAME: plotall.py
UID: p102
PGRMMR: Alice Crawford ORG: ARL
This code written at the NOAA Air Resources Laboratory
ABSTRACT: This code contains functions and classes to create concentrations as a function of time at a location from database
CTYPE: source code

-----------------------------------------------------------------------------------------------------
"""

def mod_map(gl, lonlist, latlist):
    if lonlist:
        gl.xlocator = mticker.FixedLocator([lonlist])
        gl.ylocator = mticker.FixedLocator([latlist])
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER
    #gl.xlabel_style('size': 15, 'color': 'gray'}
    #gl.ylabel_style('size': 15, 'color': 'gray', 'weight': 'bold'}

def create_map(fignum, lonlist=None):
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
   
    fig = plt.figure(fignum)
    proj = ccrs.PlateCarree()
    ax = plt.axes(projection=proj)
    gl = ax.gridlines(draw_labels=True, linewidth=2, color="gray")
    gl.xlabel_style={'size': 15, 'color': 'gray', 'weight': 'bold'}
    gl.ylabel_style={'size': 15, 'color': 'gray', 'weight': 'bold'}
    gl.ylabels_right = False
    gl.xlabels_top = False
    gl.xlocator = mticker.MaxNLocator(nbins=4, steps=[1,2,5,10,20,25],
                                      min_n_tickes=3)
    gl.ylocator = mticker.MaxNLocator(nbins=6, steps=[1,2,5,10,20,25],
                                      min_n_tickes=3)
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER
    states = cfeature.NaturalEarthFeature(
        category="cultural",
        name="admin_1_states_provinces_lines",
        scale="50m",
        facecolor="none",
    )
    ax.add_feature(states, edgecolor="gray")
    ax.add_feature(cfeature.BORDERS)
    ax.add_feature(cfeature.LAKES)
    ax.add_feature(cfeature.RIVERS)
    ax.add_feature(cfeature.COASTLINE)
    return fig, ax, gl


def set_date_ticksC(ax):
    mloc=mdates.MonthLocator()
    #minloc=mdates.WeekdayLocator()
    minloc=mdates.DayLocator(bymonthday=None, interval=2)
    #minloc=mdates.DayLocator(bymonthday=[1,5,10,15,20,25,30])
    #minloc=mdates.DayLocator(byweekday=M)
    mloc=mdates.DayLocator(bymonthday=[1,5,10,15,20,25])
    ax.xaxis.set_major_locator(mloc)
    ax.xaxis.set_minor_locator(minloc)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    start, end = ax.get_ylim()
    ax.tick_params(axis='both', which='major', labelsize=20)
    


def set_date_ticksD(ax):
    mloc=mdates.MonthLocator()
    #minloc=mdates.WeekdayLocator()
    minloc=mdates.DayLocator(bymonthday=None, interval=1)
    #minloc=mdates.DayLocator(bymonthday=[1,5,10,15,20,25,30])
    #minloc=mdates.DayLocator(byweekday=M)
    mloc=mdates.DayLocator(bymonthday=[6,8])
    ax.xaxis.set_major_locator(mloc)
    ax.xaxis.set_minor_locator(minloc)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    start, end = ax.get_ylim()
    rdate = datetime.datetime(2018,6,8,0)
    ldate = datetime.datetime(2018,6,6,0)
    ax.set_xlim(left = ldate, right=rdate)
    start, end = ax.get_xlim()
    ax.tick_params(axis='both', which='major', labelsize=20)
    print('START END', start, end)

def set_date_ticksB(ax):
    mloc=mdates.MonthLocator()
    #minloc=mdates.WeekdayLocator()
    #minloc=mdates.WeekdayLocator(byweekday=MO, interval=1)
    minloc=mdates.DayLocator(bymonthday=[1,5,10,15,20,25,30])
    #mloc=mdates.DayLocator(bymonthday=[1,10,20,30])
    ax.xaxis.set_major_locator(mloc)
    ax.xaxis.set_minor_locator(minloc)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%y'))
    start, end = ax.get_ylim()


def set_date_ticks(ax):
    mloc=mdates.MonthLocator()
    minloc=mdates.WeekdayLocator()
    ax.xaxis.set_major_locator(mloc)
    ax.xaxis.set_minor_locator(minloc)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%y'))
    start, end = ax.get_ylim()
    #ax.yaxis.set_ticks(np.arange(start, end+ny, ny))


def generate_colors():
    clrs = ['-b','-g','-c','-r','-m','-y']
    clrs.append(sns.xkcd_rgb['royal blue'])
    clrs.append(sns.xkcd_rgb['pink'])
    clrs.append(sns.xkcd_rgb['beige'])
    clrs.append(sns.xkcd_rgb['seafoam'])
    clrs.append(sns.xkcd_rgb['kelly green'])
    iii=0
    maxi=0
    done=False
    while not done:
        clr = clrs[iii]
        iii+=1
        maxi+=1
        if iii > len(clrs)-1: iii=0
        if maxi>100: done=True
        yield clr


def set_legend(ax, bw=0.8):
    # puts legend outside of plot to the right hand side.
    handles, labels = ax.get_legend_handles_labels()
    # shrink width of plot by bw%
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * bw, box.height], which='both')
    ax.legend(handles, labels, loc='center left', bbox_to_anchor=(1, 0.5),
             bbox_transform=ax.transAxes)
             #bbox_transform=plt.gcf().transFigure)

def make_patch_spines_invisible(ax):
    ax.set_frame_on(True)
    ax.patch.set_visible(False)
    for sp in ax.spines.values():
        sp.set_visible(False)

