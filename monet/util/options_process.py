import datetime


class SVparams:

    def __init__(self):
        self.d1 = None
        self.d2 = None
        self.area = None
        self.logfile = None
        self.source_chunks = 5
        self.datem_chunks = 5
        self.tcmrun = False
        self.run_duration = None

    def make_d1d2(self, drange):
        temp = drange.split(":")
        try:
            self.d1 = datetime.datetime(int(temp[0]), int(temp[1]), int(temp[2]), 0)
        except BaseException:
            print("daterange is not correct " + drange)
        try:
            self.d2 = datetime.datetime(int(temp[3]), int(temp[4]), int(temp[5]), 23)
        except BaseException:
            print("daterange is not correct " + drange)

    def make_area(self, bounds):
        if bounds:
            temp = bounds.split(":")
            latll = float(temp[0])
            lonll = float(temp[1])
            latur = float(temp[2])
            lonur = float(temp[3])
            self.area = (latll, lonll, latur, lonur)

    def add_logfile(self, tag):
        logfile = tag + '.MESSAGE.' 
        logfile += datetime.datetime.now().strftime("%Y%m%d_%H_%M.txt")
        with open(logfile, 'a') as fid:
             fid.write('-----------------------------------')
        self.logfile = logfile 

    def make_source_chunks(self, chunks):
        # source_chunks specify how many source times go into
        # an emittimes file. They will also determine the directory
        # tree structure. Since directories will be according to run start times.
        source_chunks = 24 * chunks
        if chunks < 0:
           source_chunks = -1 * chunks
           self.tcmrun = True

        self.source_chunks = source_chunks

        # run_duration specifies how long each run lasts.
        # the last emissions will occur after the time specified in
        # source_chunks,
        # METHOD A
        # The run ends at the end of the emittimes file. However,
        # a pardump file is generated which is used to initialize the next run.
        ##
        #run_duration = 24 * (chunks) + 2
        run_duration = self.source_chunks
        datemchunks =  self.source_chunks
        #ncycle = source_chunks
        # tcmruns set to last 24 hours.
        if self.tcmrun:
           run_duration = 24
        self.run_duration = run_duration

def main(options):
    svp = SVparams()
    svp.make_d1d2(options.drange)
    svp.make_area(options.bounds)
    svp.add_logfile(options.tag)
    svp.make_source_chunks(options.chunks)
    return svp


