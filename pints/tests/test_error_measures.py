#!/usr/bin/env python3
#
# Tests the error measure classes.
#
# This file is part of PINTS (https://github.com/pints-team/pints/) which is
# released under the BSD 3-clause license. See accompanying LICENSE.md for
# copyright notice and full license details.
#
from __future__ import division
import pints
import pints.toy
import unittest
import numpy as np


# Unit testing in Python 2 and 3
try:
    unittest.TestCase.assertRaisesRegex
except AttributeError:
    unittest.TestCase.assertRaisesRegex = unittest.TestCase.assertRaisesRegexp


class MiniProblem(pints.SingleOutputProblem):
    def __init__(self):
        self._t = pints.vector([1, 2, 3])
        self._v = pints.vector([-1, 2, 3])

    def n_parameters(self):
        return 3

    def evaluate(self, parameters):
        return np.array(parameters)

    def times(self):
        return self._t

    def values(self):
        return self._v


class MultiMiniProblem(pints.MultiOutputProblem):
    def __init__(self):
        self._t = pints.vector([1, 2, 3])
        self._v = pints.matrix2d(
            np.array([[-1, 2, 3], [-1, 2, 3]]).swapaxes(0, 1))

    def n_parameters(self):
        return 3

    def n_outputs(self):
        return 2

    def evaluate(self, parameters):
        return np.array([parameters, parameters]).swapaxes(0, 1)

    def times(self):
        return self._t

    def values(self):
        return self._v


class BigMiniProblem(MiniProblem):
    def __init__(self):
        super(BigMiniProblem, self).__init__()
        self._t = pints.vector([1, 2, 3, 4, 5, 6])
        self._v = pints.vector([-1, 2, 3, 4, 5, -6])

    def n_parameters(self):
        return 6


class BadMiniProblem(MiniProblem):
    def __init__(self, bad_value=float('inf')):
        super(BadMiniProblem, self).__init__()
        self._v = pints.vector([bad_value, 2, -3])

    def n_parameters(self):
        return 3


class BadErrorMeasure(pints.ErrorMeasure):
    def __init__(self, bad_value=float('-inf')):
        super(BadErrorMeasure, self).__init__()
        self._v = bad_value

    def n_parameters(self):
        return 3

    def __call__(self, parameters):
        return self._v


class MiniLogPDF(pints.LogPDF):
    def n_parameters(self):
        return 3

    def __call__(self, parameters):
        return 10

    def evaluateS1(self, parameters):
        return 10, np.array([1, 2, 3])


class TestErrorMeasures(unittest.TestCase):
    """
    Tests the ErrorMeasure classes
    """
    def __init__(self, name):
        super(TestErrorMeasures, self).__init__(name)

    def test_mean_squared_error_single(self):
        # Tests :class:`pints.MeanSquaredError` with a single output.

        # Set up problem
        model = pints.toy.ConstantModel(1)
        times = [1, 2, 3]

        # Test Case I: Input as List
        values = [1, 1, 1]
        p = pints.SingleOutputProblem(model, times, values)

        # Test for different parameters: expected = mean(input - 1) ** 2
        e = pints.MeanSquaredError(p)
        self.assertEqual(e.n_parameters(), 1)
        self.assertEqual(e([1]), 0)
        self.assertEqual(e([3]), 4)

        # Derivative of error for different parameters:
        # expected = 2 * mean(input - 1)
        p = 1
        y, dy = e.evaluateS1([p])
        self.assertEqual(y, e([p]))
        self.assertEqual(dy.shape, (1,))
        self.assertEqual(dy, 2 * (p - 1))
        p = 3
        y, dy = e.evaluateS1([p])
        self.assertEqual(y, e([p]))
        self.assertEqual(dy.shape, (1,))
        self.assertEqual(dy, 2 * (p - 1))

        # Test Case II: Input as array of shape (n_times, 1)
        values = np.array([1, 1, 1])[:, np.newaxis]
        p = pints.SingleOutputProblem(model, times, values)

        # Test for different parameters: expected = mean(input - 1) ** 2
        e = pints.MeanSquaredError(p)
        self.assertEqual(e.n_parameters(), 1)
        self.assertEqual(e([1]), 0)
        self.assertEqual(e([3]), 4)

        # Derivative of error for different parameters:
        # expected = 2 * mean(input - 1)
        p = 1
        y, dy = e.evaluateS1([p])
        self.assertEqual(y, e([p]))
        self.assertEqual(dy.shape, (1,))
        self.assertEqual(dy, 2 * (p - 1))
        p = 3
        y, dy = e.evaluateS1([p])
        self.assertEqual(y, e([p]))
        self.assertEqual(dy.shape, (1,))
        self.assertEqual(dy, 2 * (p - 1))

    def test_mean_squared_error_multi(self):
        # Tests :class:`pints.MeanSquaredError` with multiple outputs.

        # Set up problem
        model = pints.toy.ConstantModel(2)
        times = [1, 2, 3]
        values = [[1, 4], [1, 4], [1, 4]]
        p = pints.MultiOutputProblem(model, times, values)

        # Test Case I: Equal Weights on Inputs
        # Test for different parameters:
        # exp = (mean(input[0] - 1) ** 2 + mean(2 * input[1] - 4) ** 2) / 2
        e = pints.MeanSquaredError(p)
        self.assertEqual(e.n_parameters(), 2)
        self.assertEqual(e([1, 2]), 0)
        self.assertEqual(e([3, 4]), 10)     # (2 ^ 2 + 4 ^ 2) / 2 = 10

        # Derivative of error for different parameters:
        # Expectation for nth parameter:
        # expectation = [mean(input[0] - 1), mean(2 * input[1] - 4)]
        x = [1, 2]
        y, dy = e.evaluateS1(x)
        self.assertEqual(y, e(x))
        self.assertEqual(dy.shape, (2,))
        self.assertEqual(dy[0], x[0] - 1)
        self.assertEqual(dy[1], 2 * x[1] - 4)
        x = [3, 4]
        y, dy = e.evaluateS1(x)
        self.assertEqual(y, e(x))
        self.assertEqual(dy.shape, (2,))
        self.assertEqual(dy[0], x[0] - 1)
        self.assertEqual(dy[1], 2 * x[1] - 4)

        # Test Case II: Weighted Inputs
        # Check valid weights don't throw an error
        weights = [1, 2]
        e = pints.MeanSquaredError(p, weights=weights)
        self.assertEqual(e.n_parameters(), 2)

        # Test for different parameters:
        # exp = (weight[0] * mean(input[0] - 1) ** 2 +
        # weight[1] * mean(2 * input[1] - 4) ** 2) / 2
        self.assertEqual(e([1, 2]), 0)
        self.assertEqual(e([3, 4]), 18)     # (2 ^ 2 + 2 * 4 ^ 2) / 2 = 18

        # Derivative of error for different parameters:
        # Expectation for nth parameter:
        # expectation = [weight [0] * mean(input[0] - 1),
        # weight[1] * mean(2 * input[1] - 4)]
        x = [1, 2]
        y, dy = e.evaluateS1(x)
        self.assertEqual(y, e(x))
        self.assertEqual(dy.shape, (2,))
        self.assertEqual(dy[0], weights[0] * (x[0] - 1))
        self.assertEqual(dy[1], weights[1] * (2 * x[1] - 4))
        x = [3, 4]
        y, dy = e.evaluateS1(x)
        self.assertEqual(y, e(x))
        self.assertEqual(dy.shape, (2,))
        self.assertEqual(dy[0], weights[0] * (x[0] - 1))
        self.assertEqual(dy[1], weights[1] * (2 * x[1] - 4))

    def test_normalised_root_mean_squared_error(self):
        # Tests :class:`pints.NormalisedRootMeanSquaredError` with a single output.

        # Set up problem
        model = pints.toy.ConstantModel(1)
        times = [1, 2, 3]

        # Test Case I: Input as List
        values = [2, 2, 2]
        p = pints.SingleOutputProblem(model, times, values)

        # Test for different parameters:
        # expected = sqrt(mean((input - 1) ** 2)) / sqrt(mean(2 ** 2))
        e = pints.NormalisedRootMeanSquaredError(p)
        self.assertEqual(e.n_parameters(), 1)
        self.assertEqual(e([2]), 0)
        self.assertEqual(e([3]), 0.5)  # sqrt(1^2) / sqrt(2^2) = 0.5

        # Check derivatives
        self.assertRaisesRegex(
            NotImplementedError,
            '',
            e.evaluateS1, 1)

        # Test Case II: Input as array of shape (n_times, 1)
        values = [2, 2, 2]
        p = pints.SingleOutputProblem(model, times, values)

        # Test for different parameters:
        # expected = sqrt(mean((input - 2) ** 2)) / sqrt(mean(2 ** 2))
        e = pints.NormalisedRootMeanSquaredError(p)
        self.assertEqual(e.n_parameters(), 1)
        self.assertEqual(e([2]), 0)
        self.assertEqual(e([3]), 0.5)  # sqrt(2^2) / sqrt(2^2) = 0.5

        # Check derivatives
        self.assertRaisesRegex(
            NotImplementedError,
            '',
            e.evaluateS1, 1)

        # Test invalid problem
        p = MultiMiniProblem()
        self.assertRaisesRegex(
            ValueError,
            'This measure is only defined for single output problems.',
            pints.NormalisedRootMeanSquaredError, p)

    def test_probability_based_error(self):
        # Tests :class:`pints.ProbabilityBasedError`.

        p = MiniLogPDF()
        e = pints.ProbabilityBasedError(p)
        self.assertEqual(e.n_parameters(), 3)
        self.assertEqual(e([1, 2, 3]), -10)
        p = MiniProblem()
        self.assertRaises(ValueError, pints.ProbabilityBasedError, p)

        # Test derivatives
        x = [1, 2, 3]
        y, dy = e.evaluateS1(x)
        self.assertEqual(y, e(x))
        self.assertEqual(dy.shape, (3,))
        self.assertEqual(dy[0], -1)
        self.assertEqual(dy[1], -2)
        self.assertEqual(dy[2], -3)

    def test_root_mean_squared_error(self):
        # Tests :class:`pints.RootMeanSquaredError` with a single output.

        # Set up problem
        model = pints.toy.ConstantModel(1)
        times = [1, 2, 3]

        # Test Case I: Input as List
        values = [1, 1, 1]
        p = pints.SingleOutputProblem(model, times, values)

        # Test for different parameters:
        # expected = sqrt(mean((input - 1) ** 2))
        e = pints.RootMeanSquaredError(p)
        self.assertEqual(e.n_parameters(), 1)
        self.assertEqual(e([1]), 0)
        self.assertEqual(e([3]), 2)  # sqrt(2^2) = 2

        # Check derivatives
        self.assertRaisesRegex(
            NotImplementedError,
            '',
            e.evaluateS1, 1)

        # Test Case II: Input as array of shape (n_times, 1)
        values = [1, 1, 1]
        p = pints.SingleOutputProblem(model, times, values)

        # Test for different parameters:
        # expected = sqrt(mean((input - 1) ** 2))
        e = pints.RootMeanSquaredError(p)
        self.assertEqual(e.n_parameters(), 1)
        self.assertEqual(e([1]), 0)
        self.assertEqual(e([3]), 2)  # sqrt(2^2) = 2

        # Check derivatives
        self.assertRaisesRegex(
            NotImplementedError,
            '',
            e.evaluateS1, 1)

        # Test invalid problem
        p = MultiMiniProblem()
        self.assertRaisesRegex(
            ValueError,
            'This measure is only defined for single output problems.',
            pints.RootMeanSquaredError, p)

    def test_sum_of_squares_error_single(self):
        # Tests :class:`pints.MeanSquaredError` with a single output.

        # Set up problem
        model = pints.toy.ConstantModel(1)
        times = [1, 2, 3]
        values = [1, 1, 1]
        p = pints.SingleOutputProblem(model, times, values)

        # Test
        e = pints.SumOfSquaresError(p)
        self.assertEqual(e.n_parameters(), 1)
        float(e([1]))
        self.assertEqual(e([1]), 0)
        self.assertEqual(e([2]), 3)
        self.assertEqual(e([0]), 3)
        self.assertEqual(e([3]), 12)

        # Derivatives
        for x in [1, 2, 3, 4]:
            ex, dex = e.evaluateS1([x])
            r = x - 1
            self.assertEqual(ex, e([x]))
            self.assertEqual(dex.shape, (1, ))
            self.assertEqual(dex[0], 2 * 3 * r)

    def test_sum_of_squares_error_multi(self):
        # Tests :class:`pints.MeanSquaredError` with multiple outputs.

        # Set up problem
        model = pints.toy.ConstantModel(2)
        times = [1, 2, 3]
        values = [[1, 4], [1, 4], [1, 4]]
        p = pints.MultiOutputProblem(model, times, values)

        # Test
        e = pints.SumOfSquaresError(p)
        self.assertEqual(e.n_parameters(), 2)
        float(e([1, 2]))
        self.assertEqual(e([1, 2]), 0)      # 0
        self.assertEqual(e([2, 2]), 3)      # 3*(1^2+0^2) = 3
        self.assertEqual(e([2, 3]), 15)     # 3*(1^2+2^2) = 15
        self.assertEqual(e([3, 4]), 60)     # 3*(2^2+4^2) = 60

        # Derivatives
        values = np.array([[1, 4], [2, 7], [3, 10]])
        p = pints.MultiOutputProblem(model, times, values)
        e = pints.SumOfSquaresError(p)
        x = [1, 2]

        # Model outputs are 3 times [1,4]
        # Model derivatives are 3 times [[1, 0], [0, 1]]
        y, dy = p.evaluateS1(x)
        self.assertTrue(np.all(y == p.evaluate(x)))
        self.assertTrue(np.all(y[0, :] == [1, 4]))
        self.assertTrue(np.all(y[1, :] == [1, 4]))
        self.assertTrue(np.all(y[2, :] == [1, 4]))
        self.assertTrue(np.all(dy[0, :] == [[1, 0], [0, 1]]))
        self.assertTrue(np.all(dy[1, :] == [[1, 0], [0, 1]]))
        self.assertTrue(np.all(dy[2, :] == [[1, 0], [0, 1]]))

        # Check residuals
        rx = y - np.array(values)
        self.assertTrue(np.all(rx == np.array(
            [[-0, -0],
             [-1, -3],
             [-2, -6]]
        )))
        self.assertAlmostEqual(e(x), np.sum(rx**2))

        # Now with derivatives
        ex, dex = e.evaluateS1(x)

        # Check error
        self.assertTrue(np.all(ex == e(x)))

        # Check derivatives. Shape is (parameters, )
        self.assertEqual(dex.shape, (2, ))

        # Residuals are: [[0, 0], [-1, -3], [-2, -6]]
        # Derivatives are: [[1, 0], [0, 1]]
        # dex1 is: 2 * (0 - 1 - 2) * 1 = 2 * -3 * 1 = -6
        # dex2 is: 2 * (0 - 3 - 6) * 2 = 2 * -9 * 1 = -18
        self.assertEqual(dex[0], -6)
        self.assertEqual(dex[1], -18)

    def test_sum_of_squares_error_weighted(self):
        # Tests :class:`pints.MeanSquaredError` with weighted outputs.

        # Set up problem
        model = pints.toy.ConstantModel(2)
        times = [1, 2, 3]
        values = [[1, 4], [1, 4], [1, 4]]
        p = pints.MultiOutputProblem(model, times, values)

        # Test
        e = pints.SumOfSquaresError(p, weights=[1, 2])
        self.assertRaisesRegex(
            ValueError, 'Number of weights',
            pints.SumOfSquaresError, p, weights=[1, 2, 3])
        self.assertEqual(e.n_parameters(), 2)
        float(e([1, 2]))
        self.assertEqual(e([1, 2]), 0)      # 0
        self.assertEqual(e([2, 2]), 3)      # 3*(1^2*1+0^2*2) = 3
        self.assertEqual(e([2, 3]), 27)     # 3*(1^2*1+2^2*2) = 27
        self.assertEqual(e([3, 4]), 108)    # 3*(2^2*1+4^2*2) = 108

        # Derivatives
        values = np.array([[1, 4], [2, 7], [3, 10]])
        p = pints.MultiOutputProblem(model, times, values)
        w = np.array([1, 2])
        e = pints.SumOfSquaresError(p, weights=w)
        x = [1, 2]

        # Model outputs are 3 times [1, 4]
        # Model derivatives are 3 times [[1, 0], [0, 1]]
        y, dy = p.evaluateS1(x)
        self.assertTrue(np.all(y == p.evaluate(x)))
        self.assertTrue(np.all(y[0, :] == [1, 4]))
        self.assertTrue(np.all(y[1, :] == [1, 4]))
        self.assertTrue(np.all(y[2, :] == [1, 4]))
        self.assertTrue(np.all(dy[0, :] == [[1, 0], [0, 1]]))
        self.assertTrue(np.all(dy[1, :] == [[1, 0], [0, 1]]))
        self.assertTrue(np.all(dy[2, :] == [[1, 0], [0, 1]]))

        # Check residuals
        rx = y - np.array(values)
        self.assertTrue(np.all(rx == np.array(
            [[-0, -0],
             [-1, -3],
             [-2, -6]]
        )))
        self.assertAlmostEqual(e(x), np.sum(np.sum(rx**2, axis=0) * w))

        # Now with derivatives
        ex, dex = e.evaluateS1(x)

        # Check error
        self.assertAlmostEqual(ex, e(x))

        # Check derivatives. Shape is (parameters, )
        self.assertEqual(dex.shape, (2, ))

        # Residuals are: [[0, 0], [-1, -3], [-2, -6]]
        # Derivatives are: [[1, 0], [0, 1]]
        # dex1 is: 2 * (0 - 1 - 2) * 1 * 1
        #        = 2 * -3 * 1 * 1
        #        = -6
        # dex2 is: 2 * (0 - 3 - 6) * 2 * 1
        #        = 2 * -9 * 2 * 1
        #        = -36
        self.assertEqual(dex[0], -6)
        self.assertEqual(dex[1], -36)

    def test_sum_of_errors(self):
        # Tests :class:`pints.SumOfErrors`.

        e1 = pints.SumOfSquaresError(MiniProblem())
        e2 = pints.MeanSquaredError(MiniProblem())
        e3 = pints.RootMeanSquaredError(BigMiniProblem())
        e4 = pints.SumOfSquaresError(BadMiniProblem())

        # Basic use
        e = pints.SumOfErrors([e1, e2])
        x = [0, 0, 0]
        self.assertEqual(e.n_parameters(), 3)
        self.assertEqual(e(x), e1(x) + e2(x))
        e = pints.SumOfErrors([e1, e2], [3.1, 4.5])
        x = [0, 0, 0]
        self.assertEqual(e.n_parameters(), 3)
        self.assertEqual(e(x), 3.1 * e1(x) + 4.5 * e2(x))
        e = pints.SumOfErrors(
            [e1, e1, e1, e1, e1, e1], [1, 2, 3, 4, 5, 6])
        self.assertEqual(e.n_parameters(), 3)
        self.assertEqual(e(x), e1(x) * 21)
        self.assertNotEqual(e(x), 0)

        with np.errstate(all='ignore'):
            e = pints.SumOfErrors(
                [e4, e1, e1, e1, e1, e1], [10, 1, 1, 1, 1, 1])
            self.assertEqual(e.n_parameters(), 3)
            self.assertEqual(e(x), float('inf'))
            e = pints.SumOfErrors(
                [e4, e1, e1, e1, e1, e1], [0, 2, 0, 2, 0, 2])
            self.assertEqual(e.n_parameters(), 3)
            self.assertTrue(e(x), 6 * e1(x))
            e5 = pints.SumOfSquaresError(BadMiniProblem(float('-inf')))
            e = pints.SumOfErrors([e1, e5, e1], [2.1, 3.4, 6.5])
            self.assertTrue(np.isinf(e(x)))
            e = pints.SumOfErrors([e4, e5, e1], [2.1, 3.4, 6.5])
            self.assertTrue(np.isinf(e(x)))
            e5 = pints.SumOfSquaresError(BadMiniProblem(float('nan')))
            e = pints.SumOfErrors(
                [BadErrorMeasure(float('inf')), BadErrorMeasure(float('inf'))],
                [1, 1])
            self.assertEqual(e(x), float('inf'))
            e = pints.SumOfErrors(
                [BadErrorMeasure(float('inf')),
                 BadErrorMeasure(float('-inf'))],
                [1, 1])
            self.assertTrue(np.isnan(e(x)))
            e = pints.SumOfErrors(
                [BadErrorMeasure(5), BadErrorMeasure(float('nan'))], [1, 1])
            self.assertTrue(np.isnan(e(x)))
            e = pints.SumOfErrors([e1, e5, e1], [2.1, 3.4, 6.5])
            self.assertTrue(np.isnan(e(x)))
            e = pints.SumOfErrors([e4, e5, e1], [2.1, 3.4, 6.5])
            self.assertTrue(np.isnan(e(x)))

        # Wrong number of ErrorMeasures
        self.assertRaises(ValueError, pints.SumOfErrors, [], [])

        # Wrong argument types
        self.assertRaises(
            TypeError, pints.SumOfErrors, [e1, e1], [e1, 1])
        self.assertRaises(
            ValueError, pints.SumOfErrors, [e1, 3], [2, 1])

        # Mismatching sizes
        self.assertRaises(
            ValueError, pints.SumOfErrors, [e1, e1, e1], [1, 1])

        # Mismatching problem dimensions
        self.assertRaises(
            ValueError, pints.SumOfErrors, [e1, e1, e3], [1, 2, 3])

        # Single-output derivatives
        model = pints.toy.ConstantModel(1)
        times = [1, 2, 3]
        p1 = pints.SingleOutputProblem(model, times, [1, 1, 1])
        p2 = pints.SingleOutputProblem(model, times, [2, 2, 2])
        e1 = pints.SumOfSquaresError(p1)
        e2 = pints.SumOfSquaresError(p2)
        e = pints.SumOfErrors([e1, e2], [1, 2])
        x = [4]
        y, dy = e.evaluateS1(x)
        self.assertEqual(y, e(x))
        self.assertEqual(dy.shape, (1, ))
        y1, dy1 = e1.evaluateS1(x)
        y2, dy2 = e2.evaluateS1(x)
        self.assertTrue(np.all(dy == dy1 + 2 * dy2))

        # Multi-output derivatives
        model = pints.toy.ConstantModel(2)
        times = [1, 2, 3]
        p1 = pints.MultiOutputProblem(model, times, [[3, 2], [1, 7], [3, 2]])
        p2 = pints.MultiOutputProblem(model, times, [[2, 3], [3, 4], [5, 6]])
        e1 = pints.SumOfSquaresError(p1)
        e2 = pints.SumOfSquaresError(p2)
        e = pints.SumOfErrors([e1, e2], [1, 2])
        x = [4, -2]
        y, dy = e.evaluateS1(x)
        self.assertEqual(y, e(x))
        self.assertEqual(dy.shape, (2, ))
        y1, dy1 = e1.evaluateS1(x)
        y2, dy2 = e2.evaluateS1(x)
        self.assertTrue(np.all(dy == dy1 + 2 * dy2))


if __name__ == '__main__':
    unittest.main()
