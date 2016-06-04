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
        self.max_val = 1 << (m + f + 1)
        self.min_val = -self.max_val

        print "%d.%d (%d, %d)" % (self.m, self.f, self.min_val, self.max_val)

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
        return int(round(x * (1 << self.f)))

    def to_float(self, x):
        """Compute the nearest floating-point representation of fixed-point value x."""
        return int(x) / float(1 << self.f)


def ExpComb(x, y, fixed_def):
    """Combinatorial implementation of the exponential function."""

    # Compute x^2.
    x2 = fixed_def.make_signal(0)
    inst_x2 = fixed_def.fixed_mul(x2, x, x)

    # Compute x^3.
    x3 = fixed_def.make_signal(0)
    inst_x3 = fixed_def.fixed_mul(x3, x2, x)

    # Compute 1/6 of x^3.
    sixth = fixed_def.to_fixed(1.0 / 6)
    x3_6 = fixed_def.make_signal(0)
    inst_x3_6 = fixed_def.fixed_mul(x3_6, x3, sixth)

    @always_comb
    def logic():
        """Second-order Taylor expansion of the exponential function around 0."""
        y.next = (1 << fixed_def.f) + x + (x2 >> 1) + x3_6

    return instances()


def ExpSeq(x, y, clock, reset, fixed_def):
    """Sequential wrapper for the exponential function."""

    y_comb = fixed_def.make_signal(0)
    exp_inst = ExpComb(x, y_comb, fixed_def)

    @always_seq(clock.posedge, reset=reset)
    def reg_exp():
        y.next = y_comb

    return instances()


# Globals to contain simulation data for plotting.
x_vals, relerr_vals = [], []


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
        for i in range(- (1 << N) + 1, 1 << N):
            x.next = i
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
            print "x = %f (%s), test y = %f (%s), gold y = %f, relative err = %f" % (
            xf, bin(x.val), yf, bin(y.val), ygold, relerr)

            x_vals.append(xf)
            relerr_vals.append(relerr)

    return instances()


def convert():
    fixed_def = FixedDef(1, 8)

    X = fixed_def.make_signal(0)
    Y = fixed_def.make_signal(0)
    toVerilog(ExpComb, X, Y, fixed_def)

    clock = Signal(bool())
    reset = ResetSignal(1, active=0, async=True)
    toVerilog(ExpSeq, X, Y, clock, reset, fixed_def)


def simulate():
    tb = traceSignals(exp_test_bench, 8)
    sim = Simulation(tb)
    sim.run()

    # Display relative error as a function of x.
    import matplotlib.pyplot as plt
    plt.plot(x_vals, relerr_vals, '.')
    plt.xlabel("x")
    plt.ylabel("relative error")
    plt.grid()
    plt.title("8-bit fixed point exp()")
    plt.show()


if __name__ == '__main__':
    convert()
    simulate()

