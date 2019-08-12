# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import matplotlib.dates as mdates
import seaborn as sns
"""
NAME: plotall.py
UID: p102
PGRMMR: Alice Crawford ORG: ARL
This code written at the NOAA Air Resources Laboratory
ABSTRACT: This code contains functions and classes to create concentrations as a function of time at a location from database
CTYPE: source code

-----------------------------------------------------------------------------------------------------
"""
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

