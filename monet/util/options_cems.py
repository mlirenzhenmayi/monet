import matplotlib.pyplot as plt
from monet.util.svcems import SEmissions
from monet.util.ptools import create_map
from monet.util.svens import ensemble_emitimes

def emit_ens(options, tdir):

    ef.create_emitimes(
        ef.d1,
        schunks=source_chunks,
        tdir=options.tdir,
        unit=options.byunit,
        heat=options.heat,
        emit_area=options.emit_area,
    )


def get_ef(options, d1, d2, area, source_chunks, logfile):
    with open(logfile, 'a') as fid:
     fid.write('Running cems=True options\n')
    #print(options.orislist[0])
    if options.orislist[0] != "None":
        alist = options.orislist
        byarea = False
    else:
        alist = area
        byarea = True
    # instantiate object
    ef = SEmissions(
        [d1, d2],
        alist,
        area=byarea,
        tdir=options.tdir,
        spnum=options.spnum,
        tag=options.tag,
        )
     # get emissions data
     # create source_summary.csv file.
    ef.find()
    return ef


def options_cems_main(options, d1, d2, area, source_chunks, logfile,
                      ensemble=False):
    ef = get_ef(options, d1, d2, area, source_chunks, logfile)

    rfignum = ef.fignum
    if ensemble:
        ensemble_emitimes(options, options.metfmt, ef, source_chunks)
    else: 
        # create emittimes files
        ef.create_emitimes(
            ef.d1,
            schunks=source_chunks,
            tdir=options.tdir,
            unit=options.byunit,
            heat=options.heat,
            emit_area=options.emit_area,
        )
        return ef, rfignum

    # create plots of emissions
    if options.quiet == 0:
        ef.nowarning_plot(save=True, quiet=False)
    else:
        ef.nowarning_plot(save=True, quiet=True)

    rfignum = ef.fignum
    # make map
    if options.quiet == 1:
        plt.close("all")
        rfignum = 1
    if not options.obs:
        print("map fig number  " + str(rfignum))
        mapfig = plt.figure(rfignum)
        figmap, axmap = create_map(rfignum)
        ef.map(axmap)
        plt.savefig(options.tdir + "map.jpg")
        if options.quiet < 2:
            plt.show()
    return ef, rfignum
