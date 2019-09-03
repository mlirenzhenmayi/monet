# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import matplotlib.dates as mdates
import seaborn as sns
import matplotlib.pyplot as plt
"""
NAME: plotall.py
UID: p102
PGRMMR: Alice Crawford ORG: ARL
This code written at the NOAA Air Resources Laboratory
ABSTRACT: This code contains functions and classes to create concentrations as a function of time at a location from database
CTYPE: source code

-----------------------------------------------------------------------------------------------------
"""

def create_map(fignum):
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    fig = plt.figure(fignum)
    proj = ccrs.PlateCarree()
    ax = plt.axes(projection=proj)
    gl = ax.gridlines(draw_labels=True, linewidth=2, color="gray")
    gl.ylabels_right = False
    gl.xlabels_top = False
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
    return ax


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


def set_legend(ax):
    # puts legend outside of plot to the right hand side.
    handles, labels = ax.get_legend_handles_labels()
    # shrink width of plot by 80%
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(handles, labels, loc='center left', bbox_to_anchor=(1, 0.5))

