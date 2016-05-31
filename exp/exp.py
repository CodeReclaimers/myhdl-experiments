import math
from myhdl import *


class FixedDef:
    """Super-low budget signed fixed-point implementation."""
    def __init__(self, m, f):
        """
        :param m: Number of bits before the radix point.
        :param f: Number of bits after the radix point.
        """
        self.m = m
        self.f = f
        self.max_val = 1 << (m + f)
        self.min_val = -self.max_val

    def make_signal(self, init_value):
        return Signal(intbv(init_value, min=self.min_val, max=self.max_val))

    def fixed_mul(self, z, x, y):
        @always_comb
        def logic():
            """Return the product of the fixed point inputs x and y via z."""
            z.next = (x * y) >> self.f

        return logic

    def to_fixed(self, x):
        """Compute the nearest fixed-point representation of x."""
        return int(x * (1 << self.f))

    def to_float(self, x):
        """Compute the nearest floating-point representation of fixed-point value x."""
        return int(x) / float(1 << self.f)


def ExpComb(x, y, fixed_def):
    x2 = fixed_def.make_signal(0)
    inst_x2 = fixed_def.fixed_mul(x2, x, x)

    @always_comb
    def logic():
        """Second-order Taylor expansion of the exponential function around 0."""
        y.next = (1 << fixed_def.f) + x + (x2 >> 1)

    return instances()


def ExpSeq(x, y, clock, reset, fixed_def):
    y_comb = fixed_def.make_signal(0)
    exp_inst = ExpComb(x, y_comb, fixed_def)

    @always_seq(clock.posedge, reset=reset)
    def reg_exp():
        y.next = y_comb

    return instances()


def exp_test_bench(N):
    reset = ResetSignal(1, active=0, async=True)

    fixed_def = FixedDef(1, N)
    y = fixed_def.make_signal(0)
    x = fixed_def.make_signal(0)
    clock = Signal(bool(0))

    exp_inst = ExpSeq(x, y, clock, reset, fixed_def)

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
            xf = fixed_def.to_float(x.val)
            yf = fixed_def.to_float(y.val)
            ygold = math.exp(fixed_def.to_float(x.val))
            relerr = (yf - ygold) / ygold
            print "x = %f (%s), test y = %f (%s), gold y = %f, relative err = %f" % (xf, bin(x), yf, bin(y), ygold, relerr)

    return instances()


if 0:
    fixed_def = FixedDef(1, 5)

    X = fixed_def.make_signal(0)
    Y = fixed_def.make_signal(0)
    toVerilog(ExpComb, X, Y, fixed_def)

    clock = Signal(bool())
    reset = ResetSignal(1, active=0, async=True)
    toVerilog(ExpSeq, X, Y, clock, reset, fixed_def)

else:
    tb = traceSignals(exp_test_bench, 10)
    sim = Simulation(tb)
    sim.run()


