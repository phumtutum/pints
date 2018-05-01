#
# Repressilator model.
#
# This file is part of PINTS.
#  Copyright (c) 2017, University of Oxford.
#  For licensing information, see the LICENSE file distributed with the PINTS
#  software package.
#
#
from __future__ import absolute_import, division
from __future__ import print_function, unicode_literals
import numpy as np
import pints
from scipy.integrate import odeint


class RepressilatorModel(pints.ForwardModelS1):
    """
    The "Repressilator" model describes oscillations in a network of proteins
    that suppress their own creation [1].

    The formulation used here is taken from [3] and analysed in [4]. It has
    three protein states (pi), each encoded by mRNA (mi). Once expressed, they
    suppress each other:

    .. math::
        \\dot{m_0} = -m_0 + \\frac{\\alpha}{1 + p_2^n} + \\alpha_0

        \\dot{m_1} = -m_1 + \\frac{\\alpha}{1 + p_0^n} + \\alpha_0

        \\dot{m_2} = -m_2 + \\frac{\\alpha}{1 + p_1^n} + \\alpha_0

        \\dot{p_0} = -\\beta (p_0 - m_0)

        \\dot{p_1} = -\\beta (p_1 - m_1)

        \\dot{p_2} = -\\beta (p_2 - m_2)

    With parameters ``alpha_0``, ``alpha``, ``beta``, and ``n``.

    Only the mRNA states are visible as output.

    Arguments:

    ``y0``
        The system's initial state, must have 6 entries all >=0.

    References:

    [1] A Synthetic Oscillatory Network of Transcriptional Regulators. Elowitz,
    Leibler (2000) Nature

    [2] https://en.wikipedia.org/wiki/Repressilator

    [3] Dynamic models in biology. Ellner, Guckenheimer (2006) Princeton
    University Press

    [4] Approximate Bayesian computation scheme for parameter inference and
    model selection in dynamical systems. Toni, Welch, Strelkowa, Ipsen, Stumpf
    (2009) J. R. Soc. Interface.
    """

    def __init__(self, y0=None):
        super(RepressilatorModel, self).__init__()

        # Check initial values
        if y0 is None:
            # Toni et al.:
            self._y0 = np.array([0, 0, 0, 2, 1, 3])
            # Figure 42 in book
            #self._y0 = np.array([0.2, 0.1, 0.3, 0.1, 0.4, 0.5], dtype=float)
        else:
            self._y0 = np.array(y0, dtype=float)
            if len(self._y0) != 6:
                raise ValueError('Initial value must have size 6.')
            if np.any(self._y0 < 0):
                raise ValueError('Initial states can not be negative.')

    def n_parameters(self):
        """ See :meth:`pints.ForwardModel.n_parameters)`. """
        return 4

    def n_outputs(self):
        """ See :meth:`pints.ForwardModel.outputs()`. """
        return 3

    def _rhs(self, y, t, alpha_0, alpha, beta, n):
        """
        Calculates the model RHS.
        """
        dy = np.zeros(6)
        dy[0] = -y[0] + alpha / (1 + y[5]**n) + alpha_0
        dy[1] = -y[1] + alpha / (1 + y[3]**n) + alpha_0
        dy[2] = -y[2] + alpha / (1 + y[4]**n) + alpha_0
        dy[3] = -beta * (y[3] - y[0])
        dy[4] = -beta * (y[4] - y[1])
        dy[5] = -beta * (y[5] - y[2])
        return dy

    def simulate(self, parameters, times):
        """ See :meth:`pints.ForwardModel.simulate()`. """
        alpha_0, alpha, beta, n = parameters
        y = odeint(self._rhs, self._y0, times, (alpha_0, alpha, beta, n))
        return y[:, :3]

    def suggested_parameters(self):
        """
        Returns a suggested set of parameters for this toy model.
        """
        # Toni et al.:
        return np.array([1, 1000, 5, 2])
        # Figure 42 in book:
        #return np.array([0, 50, 0.2, 2])

    def suggested_times(self):
        """
        Returns a suggested set of simulation times for this toy model.
        """
        # Toni et al.:
        return np.linspace(0, 40, 400)
        # Figure 42 in book:
        #return np.linspace(0, 300, 600)

