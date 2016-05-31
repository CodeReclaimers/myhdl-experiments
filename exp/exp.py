import math
from myhdl import *


def to_fixed(x, N):
    return int(x * (1 << N))


def to_float(x, N):
    return int(x) / float(1 << N)


def fixed_mul(z, x, y, N):
    @always_comb
    def logic():
        z.next = (x * y) >> N

    return logic


def ExpComb(x, y, N):
    x2 = Signal(intbv(0)[N:])
    inst_x2 = fixed_mul(x2, x, x, N)

    @always_comb
    def logic():
        y.next = (1 << N) + x + (x2 >> 1)

    return instances()


def ExpSeq(x, y, clock, reset, N):
    y_comb = Signal(intbv(0)[N+1:])
    exp_inst = ExpComb(x, y_comb, N)

    @always_seq(clock.posedge, reset=reset)
    def reg_exp():
        y.next = y_comb

    return instances()




def exp_test_bench(N):
    reset = ResetSignal(1, active=0, async=True)

    y = Signal(intbv(0)[N+1:])
    x = Signal(intbv(0)[N+1:])
    clock = Signal(bool(0))

    exp_inst = ExpSeq(x, y, clock, reset, N)
    #exp_inst = ExpComb(x, y, N)

    period = delay(1)

    @always(period)
    def clock_gen():
        clock.next = not clock

    @instance
    def stimulus():
        yield clock.negedge
        for i in range(N):
            x.next = 1 << i
            yield clock.negedge
        raise StopSimulation

    @instance
    def monitor():
        while 1:
            yield clock.posedge
            yield delay(1)
            xf = to_float(x.val, N)
            yf = to_float(y.val, N)
            ygold = math.exp(to_float(x.val, N))
            relerr = (yf - ygold) / ygold
            print "x = %f (%s), test y = %f (%s), gold y = %f, relative err = %f" % (xf, bin(x), yf, bin(y), ygold, relerr)

    return instances()


if 0:
    bits = 5
    X = Signal(intbv(0)[bits:])
    Y = Signal(intbv(0)[bits:])
    toVerilog(ExpComb, X, Y, bits)

    clock = Signal(bool())
    reset = ResetSignal(1, active=0, async=True)
    toVerilog(ExpSeq, X, Y, clock, reset, bits)

else:
    tb = traceSignals(exp_test_bench, 10)
    sim = Simulation(tb)
    sim.run()


