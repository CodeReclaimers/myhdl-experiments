"""
This module implements a spiking neuron based on the model described by:

Izhikevich, E. M.
Simple Model of Spiking Neurons
IEEE TRANSACTIONS ON NEURAL NETWORKS, VOL. 14, NO. 6, NOVEMBER 2003
"""

import pylab
from myhdl import *

################################################################################
# Low-budget fixed-point implementation.

def fixed_mul(x, y, Fshift):
    """Multiply fixed-point representations of x and y, returning
    a fixed-point representation of the result."""
    return (x * y) >> Fshift


def to_fixed(x, Fshift):
    """Convert a floating point input to the nearest fixed-point representation."""
    return int(x * (1 << Fshift))


def to_float(x, Fshift):
    """Convert a fixed-point input to the nearest floating-point representation."""
    return int(x) / float(1 << Fshift)

################################################################################


################################################################################
# Izhikevitch model derivatives.

def compute_dv(I, u, v, dt, Fshift):
    """Compute (dv/dt) * dt."""
    c1 = to_fixed(0.04, Fshift)
    c2 = to_fixed(5, Fshift)
    c3 = to_fixed(140, Fshift)

    v2 = fixed_mul(v, v, Fshift)
    return fixed_mul(dt,
                    fixed_mul(c1, v2, Fshift) + fixed_mul(c2, v, Fshift) + c3 - u + I,
                    Fshift)


def compute_du(u, v, a, b, dt, Fshift):
    """Compute (du/dt) * dt."""
    b_v = fixed_mul(b, v, Fshift)
    dt_a = fixed_mul(dt, a, Fshift)
    return fixed_mul(dt_a, b_v - u, Fshift)

################################################################################

# Containers for matplotlib data.
t_values = []
u_values = []
v_values = []
I_values = []
out_values = []


def neuron_module(clk, reset, I, output, a, b, c, d, dt, Fshift):
    """
    Izhikevitch neuron behavior.
    I: input current
    output: output spike (bool, high for a spike)
    a, b, c, d: Izhikevitch neuron parameters
    dt: milliseconds of simulated time per clock
    Fshift: number of bits after the decimal
    """
    a_fix = to_fixed(a, Fshift)
    b_fix = to_fixed(b, Fshift)
    c_fix = to_fixed(c, Fshift)
    d_fix = to_fixed(d, Fshift)
    dt_fix = to_fixed(dt, Fshift)

    threshold = to_fixed(30.0, Fshift)

    max_val = 1 << (Fshift + 7)

    v = Signal(intbv(c_fix, min=-max_val, max=max_val))
    u = Signal(intbv(fixed_mul(v, b_fix, Fshift), min=-max_val, max=max_val))

    @always_seq(clk.posedge, reset=reset)
    def neuron():
        dv = compute_dv(I, u, v, dt_fix, Fshift)
        updated_v = v + dv
        if updated_v > threshold:
            v.next = c_fix
            u.next = u + d_fix
            output.next = True
        else:
            du = compute_du(u, v, a_fix, b_fix, dt_fix, Fshift)
            v.next = updated_v
            u.next = u + du
            output.next = False

        t_values.append(now() * 1.0e-3)
        u_values.append(to_float(u, Fshift))
        v_values.append(to_float(v, Fshift))
        I_values.append(to_float(I, Fshift))
        out_values.append(output)

    return neuron


def iz_test_bench(a, b, c, d, dt, Fshift):
    max_val = 1 << (Fshift + 7)

    I = Signal(intbv(0, min=-max_val, max=max_val))
    output = Signal(bool(0))

    clk = Signal(bool(0))
    reset = ResetSignal(1, active=0, async=True)

    neuron_instance = neuron_module(clk, reset, I, output, a, b, c, d, dt, Fshift)

    @always(delay(50))
    def clkgen():
        clk.next = not clk

    @instance
    def stimulus():
        I.next = 0
        yield delay(10000)
        I.next = to_fixed(10.0, Fshift)
        yield delay(100000)
        I.next = 0
        yield delay(10000)

        pylab.figure(1)
        pylab.subplot(311)
        pylab.title("MyHDL Izhikevitch neuron (chattering)")
        pylab.plot(t_values, v_values, label="v")
        pylab.ylabel('membrane potential (mv)')
        pylab.grid()
        pylab.subplot(312)
        pylab.plot(t_values, u_values, label="u")
        pylab.ylabel("recovery variable")
        pylab.grid()
        pylab.subplot(313)
        pylab.plot(t_values, I_values, label="I")
        pylab.grid()
        pylab.ylabel("input current")
        pylab.xlabel("time (usec)")
        pylab.show()

        raise StopSimulation

    return clkgen, stimulus, neuron_instance


# Uncomment definitions of a, b, c, d to choose different neuron types.

# Regular spiking
#a, b, c, d = 0.02, 0.2, -65.0, 8.0

# Fast spiking
#a, b, c, d = 0.1, 0.2, -65.0, 2.0

#intrinsically bursting
#a, b, c, d =0.02, 0.2, -55.0, 4.0

# chattering
a, b, c, d = 0.02, 0.2, -50.0, 2.0

# low-threshold spiking
#a, b, c, d = 0.02, 0.25, -65, 2.0

# thalamo-cortical
#a, b, c, d = 0.02, 0.25, -65.0, 0.05

# resonator
#a, b, c, d = 0.1, 0.26, -65.0, 2.0

# Time step (msec in simulated time per clock).
dt = 0.2

sim = Simulation(traceSignals(iz_test_bench, a, b, c, d, dt, 11))
sim.run()
