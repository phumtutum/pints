#
# Sub-module containing several optimisation routines
#
# This file is part of PINTS.
#  Copyright (c) 2017-2018, University of Oxford.
#  For licensing information, see the LICENSE file distributed with the PINTS
#  software package.
#
from __future__ import absolute_import, division
from __future__ import print_function, unicode_literals
import pints
import numpy as np


class Optimiser(pints.Loggable):
    """
    Base class for optimisers implementing an ask-and-tell interface.

    Optimisers are initialised using the arguments:

    ``x0``
        A starting point for searches in the parameter space. This value may be
        used directly (for example as the initial position of a particle in
        :class:`PSO`) or indirectly (for example as the center of a
        distribution in :class:`XNES`).
    ``sigma0=None``
        An optional initial standard deviation around ``x0``. Can be specified
        either as a scalar value (one standard deviation for all coordinates)
        or as an array with one entry per dimension. Not all methods will use
        this information.
    ``boundaries=None``
        An optional set of boundaries on the parameter space.

    All optimisers implement the :class:`pints.Loggable` interface.
    """
    def __init__(self, x0, sigma0=None, boundaries=None):

        # Get dimension
        self._dimension = len(x0)
        if self._dimension < 1:
            raise ValueError('Problem dimension must be greater than zero.')

        # Store boundaries
        self._boundaries = boundaries
        if self._boundaries:
            if self._boundaries.n_parameters() != self._dimension:
                raise ValueError(
                    'Boundaries must have same dimension as starting point.')

        # Store initial position
        self._x0 = pints.vector(x0)
        if self._boundaries:
            if not self._boundaries.check(self._x0):
                raise ValueError(
                    'Initial position must lie within given boundaries.')

        # Check initial standard deviation
        if sigma0 is None:
            # Set a standard deviation
            if self._boundaries:
                # Use boundaries to guess
                self._sigma0 = (1 / 6) * self._boundaries.range()
            else:
                # Use initial position to guess at parameter scaling
                self._sigma0 = (1 / 3) * np.abs(self._x0)
                # But add 1 for any initial value that's zero
                self._sigma0 += (self._sigma0 == 0)
            self._sigma0.setflags(write=False)

        elif np.isscalar(sigma0):
            # Single number given, convert to vector
            sigma0 = float(sigma0)
            if sigma0 <= 0:
                raise ValueError(
                    'Initial standard deviation must be greater than zero.')
            self._sigma0 = np.ones(self._dimension) * sigma0
            self._sigma0.setflags(write=False)

        else:
            # Vector given
            self._sigma0 = pints.vector(sigma0)
            if len(self._sigma0) != self._dimension:
                raise ValueError(
                    'Initial standard deviation must be None, scalar, or have'
                    ' dimension ' + str(self._dimension) + '.')
            if np.any(self._sigma0 <= 0):
                raise ValueError(
                    'Initial standard deviations must be greater than zero.')

    def ask(self):
        """
        Returns a list of positions in the search space to evaluate.
        """
        raise NotImplementedError

    def fbest(self):
        """
        Returns the objective function evaluated at the current best position.
        """
        raise NotImplementedError

    def name(self):
        """
        Returns this method's full name.
        """
        raise NotImplementedError

    def running(self):
        """
        Returns ``True`` if this an optimisation is in progress.
        """
        raise NotImplementedError

    def stop(self):
        """
        Checks if this method has run into trouble and should terminate.
        Returns ``False`` if everything's fine, or a short message (e.g.
        "Ill-conditioned matrix.") if the method should terminate.
        """
        return False

    def tell(self, fx):
        """
        Performs an iteration of the optimiser algorithm, using the evaluations
        ``fx`` of the points ``x`` previously specified by ``ask``.
        """
        raise NotImplementedError

    def xbest(self):
        """
        Returns the current best position.
        """
        raise NotImplementedError


class PopulationBasedOptimiser(Optimiser):
    """
    *Extends:* :class:`PopulationBasedOptimiser`

    Base class for optimisers that work by moving multiple points through the
    search space.
    """
    def __init__(self, x0, sigma0=None, boundaries=None):
        super(PopulationBasedOptimiser, self).__init__(x0, sigma0, boundaries)

        # Set initial population size using heuristic
        self._population_size = self._suggested_population_size()

    def population_size(self):
        """
        Returns this optimiser's population size.

        If no explicit population size has been set, ``None`` may be returned.
        Once running, the correct value will always be returned.
        """
        return self._population_size

    def set_population_size(self, population_size=None):
        """
        Sets a population size to use in this optimisation.

        If `population_size` is set to ``None``, the population size will be
        set using the heuristic :meth:`suggested_population_size()`.
        """
        if self.running():
            raise Exception('Cannot change population size during run.')

        # Check population size or set using heuristic
        if population_size is not None:
            population_size = int(population_size)
            if population_size < 1:
                raise ValueError('Population size must be at least 1.')

        # Store
        self._population_size = population_size

    def suggested_population_size(self, round_up_to_multiple_of=None):
        """
        Returns a suggested population size for this method, based on the
        dimension of the search space (e.g. the parameter space).

        If the optional argument ``round_up_to_multiple_of`` is set to an
        integer greater than 1, the method will round up the estimate to a
        multiple of that number. This can be useful to obtain a population size
        based on e.g. the number of worker processes used to perform objective
        function evaluations.
        """
        population_size = self._suggested_population_size()

        if round_up_to_multiple_of is not None:
            n = int(round_up_to_multiple_of)
            if n > 1:
                population_size = n * (((population_size - 1) // n) + 1)

        return population_size

    def _suggested_population_size(self):
        """
        Returns a suggested population size for use by
        :meth:`suggested_population_size`.
        """
        raise NotImplementedError


class Optimisation(object):
    """
    Finds the parameter values that minimise an :class:`ErrorMeasure` or
    maximise a :class:`LogPDF`.

    Arguments:

    ``function``
        An :class:`pints.ErrorMeasure` or a :class:`pints.LogPDF` that
        evaluates points in the parameter space.
    ``x0``
        The starting point for searches in the parameter space. This value may
        be used directly (for example as the initial position of a particle in
        :class:`PSO`) or indirectly (for example as the center of a
        distribution in :class:`XNES`).
    ``sigma0=None``
        An optional initial standard deviation around ``x0``. Can be specified
        either as a scalar value (one standard deviation for all coordinates)
        or as an array with one entry per dimension. Not all methods will use
        this information.
    ``boundaries=None``
        An optional set of boundaries on the parameter space.
    ``method=None``
        The class of :class:`pints.Optimiser` to use for the optimisation.
        If no method is specified, :class:`CMAES` is used.

    """
    def __init__(
            self, function, x0, sigma0=None, boundaries=None, method=None):

        # Check dimension of x0 against function
        if function.n_parameters() != len(x0):
            raise ValueError(
                'Starting point must have same dimension as function to'
                ' optimise.')

        # Check if minimising or maximising
        self._minimising = not isinstance(function, pints.LogPDF)

        # Store function
        if self._minimising:
            self._function = function
        else:
            self._function = pints.ProbabilityBasedError(function)
        del(function)

        # Create optimiser
        if method is None:
            method = pints.CMAES
        elif not issubclass(method, pints.Optimiser):
            raise ValueError('Method must be subclass of pints.Optimiser.')
        self._optimiser = method(x0, sigma0, boundaries)

        # Logging
        self._log_to_screen = True
        self._log_filename = None
        self._log_csv = False

        # Parallelisation
        self._parallel = False
        self._n_workers = 1
        self.set_parallel()

        #
        # Stopping criteria
        #

        # Maximum iterations
        self._max_iterations = None
        self.set_max_iterations()

        # Maximum unchanged iterations
        self._max_unchanged_iterations = None
        self._min_significant_change = 1
        self.set_max_unchanged_iterations()

        # Threshold value
        self._threshold = None

    def max_iterations(self):
        """
        Returns the maximum iterations if this stopping criterion is set, or
        ``None`` if it is not. See :meth:`set_max_iterations()`.
        """
        return self._max_iterations

    def max_unchanged_iterations(self):
        """
        Returns a tuple ``(iterations, threshold)`` specifying a maximum
        unchanged iterations stopping criterion, or ``(None, None)`` if no such
        criterion is set. See :meth:`set_max_unchanged_iterations()`.
        """
        if self._max_unchanged_iterations is None:
            return (None, None)
        return (self._max_unchanged_iterations, self._min_significant_change)

    def optimiser(self):
        """
        Returns the underlying optimiser object, allowing detailed
        configuration.
        """
        return self._optimiser

    def parallel(self):
        """
        Returns the number of parallel worker processes this routine will be
        run on, or ``False`` if parallelisation is disabled.
        """
        return self._n_workers if self._parallel else False

    def run(self):
        """
        Runs the optimisation, returns a tuple ``(xbest, fbest)``.
        """
        # Check stopping criteria
        has_stopping_criterion = False
        has_stopping_criterion |= (self._max_iterations is not None)
        has_stopping_criterion |= (self._max_unchanged_iterations is not None)
        has_stopping_criterion |= (self._threshold is not None)
        if not has_stopping_criterion:
            raise ValueError('At least one stopping criterion must be set.')

        # Iterations and function evaluations
        iteration = 0
        evaluations = 0

        # Unchanged iterations count (used for stopping or just for
        # information)
        unchanged_iterations = 0

        # Create evaluator object
        if self._parallel:
            # Get number of workers
            n_workers = self._n_workers

            # For population based optimisers, don't use more workers than
            # particles!
            if isinstance(self._optimiser, PopulationBasedOptimiser):
                n_workers = min(n_workers, self._optimiser.population_size())
            evaluator = pints.ParallelEvaluator(
                self._function, n_workers=n_workers)
        else:
            evaluator = pints.SequentialEvaluator(self._function)

        # Keep track of best position and score
        fbest = float('inf')

        # Internally we always minimise! Keep a 2nd value to show the user
        fbest_user = fbest if self._minimising else -fbest

        # Set up progress reporting
        next_message = 0
        message_warm_up = 3
        message_interval = 20

        # Start logging
        logging = self._log_to_screen or self._log_filename
        if logging:
            if self._log_to_screen:
                # Show direction
                if self._minimising:
                    print('Minimising error measure')
                else:
                    print('Maximising LogPDF')

                # Show method
                print('using ' + str(self._optimiser.name()))

                # Show parallelisation
                if self._parallel:
                    print('Running in parallel with ' + str(n_workers) +
                          ' worker processes.')
                else:
                    print('Running in sequential mode.')

            # Show population size
            pop_size = 1
            if isinstance(self._optimiser, PopulationBasedOptimiser):
                pop_size = self._optimiser.population_size()
                if self._log_to_screen:
                    print('Population size: ' + str(pop_size))

            # Set up logger
            logger = pints.Logger()
            if not self._log_to_screen:
                logger.set_stream(None)
            if self._log_filename:
                logger.set_filename(self._log_filename, csv=self._log_csv)

            # Add fields to log
            max_iter_guess = max(self._max_iterations or 0, 10000)
            max_eval_guess = max_iter_guess * pop_size
            logger.add_counter('Iter.', max_value=max_iter_guess)
            logger.add_counter('Eval.', max_value=max_eval_guess)
            logger.add_float('Best')
            self._optimiser._log_init(logger)
            logger.add_time('Time m:s')

        # Start searching
        timer = pints.Timer()
        running = True
        try:
            while running:
                # Get points
                xs = self._optimiser.ask()

                # Calculate scores
                fs = evaluator.evaluate(xs)

                # Perform iteration
                self._optimiser.tell(fs)

                # Check if new best found
                fnew = self._optimiser.fbest()
                if fnew < fbest:
                    # Check if this counts as a significant change
                    if np.abs(fnew - fbest) < self._min_significant_change:
                        unchanged_iterations += 1
                    else:
                        unchanged_iterations = 0

                    # Update best
                    fbest = fnew

                    # Update user value of fbest
                    fbest_user = fbest if self._minimising else -fbest
                else:
                    unchanged_iterations += 1

                # Update evaluation count
                evaluations += len(fs)

                # Show progress
                if logging and iteration >= next_message:
                    # Log state
                    logger.log(iteration, evaluations, fbest_user)
                    self._optimiser._log_write(logger)
                    logger.log(timer.time())

                    # Choose next logging point
                    if iteration < message_warm_up:
                        next_message = iteration + 1
                    else:
                        next_message = message_interval * (
                            1 + iteration // message_interval)

                # Update iteration count
                iteration += 1

                #
                # Check stopping criteria
                #

                # Maximum number of iterations
                if (self._max_iterations is not None and
                        iteration >= self._max_iterations):
                    running = False
                    halt_message = ('Halting: Maximum number of iterations ('
                                    + str(iteration) + ') reached.')

                # Maximum number of iterations without significant change
                halt = (self._max_unchanged_iterations is not None and
                        unchanged_iterations >= self._max_unchanged_iterations)
                if halt:
                    running = False
                    halt_message = ('Halting: No significant change for ' +
                                    str(unchanged_iterations) + ' iterations.')

                # Threshold value
                if self._threshold is not None and fbest < self._threshold:
                    running = False
                    halt_message = ('Halting: Objective function crossed'
                                    ' threshold: ' + str(self._threshold) +
                                    '.')

                # Error in optimiser
                error = self._optimiser.stop()
                if error:
                    running = False
                    halt_message = ('Halting: ' + str(error))
        except (Exception, SystemExit, KeyboardInterrupt):  # pragma: no cover
            # Unexpected end!
            # Show last result and exit
            print('\n' + '-' * 40)
            print('Unexpected termination.')
            print('Current best score: ' + str(fbest))
            print('Current best position:')
            for p in self._optimiser.xbest():
                print(pints.strfloat(p))
            print('-' * 40)
            raise

        # Log final values and show halt message
        if logging:
            logger.log(iteration, evaluations, fbest_user)
            self._optimiser._log_write(logger)
            logger.log(timer.time())
            if self._log_to_screen:
                print(halt_message)

        # Return best position and score
        return self._optimiser.xbest(), fbest_user

    def set_log_to_file(self, filename=None, csv=False):
        """
        Enables logging to file when a filename is passed in, disables it if
        ``filename`` is ``False`` or ``None``.

        The argument ``csv`` can be set to ``True`` to write the file in comma
        separated value (CSV) format. By default, the file contents will be
        similar to the output on screen.
        """
        if filename:
            self._log_filename = str(filename)
            self._log_csv = True if csv else False
        else:
            self._log_filename = None
            self._log_csv = False

    def set_log_to_screen(self, enabled):
        """
        Enables or disables logging to screen.
        """
        self._log_to_screen = True if enabled else False

    def set_max_iterations(self, iterations=10000):
        """
        Adds a stopping criterion, allowing the routine to halt after the
        given number of `iterations`.

        This criterion is enabled by default. To disable it, use
        `set_max_iterations(None)`.
        """
        if iterations is not None:
            iterations = int(iterations)
            if iterations < 0:
                raise ValueError(
                    'Maximum number of iterations cannot be negative.')
        self._max_iterations = iterations

    def set_max_unchanged_iterations(self, iterations=200, threshold=1e-11):
        """
        Adds a stopping criterion, allowing the routine to halt if the
        objective function doesn't change by more than `threshold` for the
        given number of `iterations`.

        This criterion is enabled by default. To disable it, use
        `set_max_unchanged_iterations(None)`.
        """
        if iterations is not None:
            iterations = int(iterations)
            if iterations < 0:
                raise ValueError(
                    'Maximum number of iterations cannot be negative.')

        threshold = float(threshold)
        if threshold < 0:
            raise ValueError('Minimum significant change cannot be negative.')

        self._max_unchanged_iterations = iterations
        self._min_significant_change = threshold

    def set_parallel(self, parallel=False):
        """
        Enables/disables parallel evaluation.

        If ``parallel=True``, the method will run using a number of worker
        processes equal to the detected cpu core count. The number of workers
        can be set explicitly by setting ``parallel`` to an integer greater
        than 0.
        Parallelisation can be disabled by setting ``parallel`` to ``0`` or
        ``False``.
        """
        if parallel is True:
            self._parallel = True
            self._n_workers = pints.ParallelEvaluator.cpu_count()
        elif parallel >= 1:
            self._parallel = True
            self._n_workers = int(parallel)
        else:
            self._parallel = False
            self._n_workers = 1

    def set_threshold(self, threshold):
        """
        Adds a stopping criterion, allowing the routine to halt once the
        objective function goes below a set `threshold`.

        This criterion is disabled by default, but can be enabled by calling
        this method with a valid `threshold`. To disable it, use
        `set_treshold(None)`.
        """
        if threshold is None:
            self._threshold = None
        else:
            self._threshold = float(threshold)

    def threshold(self):
        """
        Returns the threshold stopping criterion, or ``None`` if no threshold
        stopping criterion is set. See :meth:`set_threshold()`.
        """
        return self._threshold


def optimise(function, x0, sigma0=None, boundaries=None, method=None):
    """
    Finds the parameter values that minimise an :class:`ErrorMeasure` or
    maximise a :class:`LogPDF`.

    Arguments:

    ``function``
        An :class:`pints.ErrorMeasure` or a :class:`pints.LogPDF` that
        evaluates points in the parameter space.
    ``x0``
        The starting point for searches in the parameter space. This value may
        be used directly (for example as the initial position of a particle in
        :class:`PSO`) or indirectly (for example as the center of a
        distribution in :class:`XNES`).
    ``sigma0=None``
        An optional initial standard deviation around ``x0``. Can be specified
        either as a scalar value (one standard deviation for all coordinates)
        or as an array with one entry per dimension. Not all methods will use
        this information.
    ``boundaries=None``
        An optional set of boundaries on the parameter space.
    ``method=None``
        The class of :class:`pints.Optimiser` to use for the optimisation.
        If no method is specified, :class:`CMAES` is used.

    Returns a tuple ``(xbest, fbest)``.
    """
    return Optimisation(function, x0, sigma0, boundaries, method).run()


class TriangleWaveTransform(object):
    """
    Transforms from unbounded to bounded parameter space using a periodic
    triangle-wave transform.

    Note: The transform is applied _inside_ optimisation methods, there is no
    need to wrap this around your own problem or score function.

    This can be applied as a transformation on ``x`` to implement boundaries in
    methods with no natural boundary mechanism. It effectively mirrors the
    search space at every boundary, leading to a continuous (but non-smooth)
    periodic landscape. While this effectively creates an infinite number of
    minima/maxima, each one maps to the same point in parameter space.

    It should work well for that maintain a single search position or a single
    search distribution (e.g. :class:`CMAES`, :class:`xNES`, :class:`SNES`),
    which will end up in one of the many mirror images. However, for methods
    that use independent search particles (e.g. :class:`PSO`) it could lead to
    a scattered population, with different particles exploring different mirror
    images. Other strategies should be used for such problems.
    """
    def __init__(self, boundaries):
        self._lower = boundaries.lower()
        self._upper = boundaries.upper()
        self._range = self._upper - self._lower
        self._range2 = 2 * self._range

    def __call__(self, x):
        y = np.remainder(x - self._lower, self._range2)
        z = np.remainder(y, self._range)
        return ((self._lower + z) * (y < self._range)
                + (self._upper - z) * (y >= self._range))


def curve_fit(f, x, y, p0, boundaries=None, threshold=None, max_iter=None,
              max_unchanged=200, verbose=False, parallel=False, method=None):
    """
    Fits a function ``f(x, *p)`` to a dataset ``(x, y)`` by finding the value
    of ``p`` for which ``sum((y - f(x, *p))**2) / n`` is minimised (where ``n``
    is the number of entries in ``y``).

    Example:

        import numpy as np
        import pints

        def f(x, a, b, c):
            return a + b * x + c * x ** 2

        x = np.linspace(-5, 5, 100)
        y = f(x, 1, 2, 3) + np.random.normal(0, 1)

        p0 = [0, 0, 0]
        popt = pints.curve_fit(f, x, y, p0)

    Arguments:

    ``f``
        A function or callable class to be minimised.
    ``x``
        The values of an independent variable, at which ``y`` was recorded.
    ``y``
        Measured values ``y = f(x, p) + noise``.
    ``p0``
        An initial guess for the optimal parameters ``p``.
    ``boundaries``
        An optional :class:`pints.Boundaries` object or a tuple
        ``(lower, upper)`` specifying lower and upper boundaries for the
        search. If no boundaries are provided an unbounded search is run.
    ``threshold``
        An optional absolute threshold stopping criterium.
    ``max_iter``
        An optional maximum number of iterations stopping criterium.
    ``max_unchanged=200``
        A stopping criterion based on the maximum number of successive
        iterations without a signficant change in ``f`` (see
        :meth:`pints.Optimisation`).
    ``verbose=False``
        Set to ``True`` to print progress messages to the screen.
    ``parallel=False``
        Allows parallelisation to be enabled.
        If set to ``True``, the evaluations will happen in parallel using a
        number of worker processes equal to the detected cpu core count. The
        number of workers can be set explicitly by setting ``parallel`` to an
        integer greater than 0.
    ``method``
        The :class:`pints.Optimiser` to use. If no method is specified,
        ``pints.CMAES`` is used.

    Returns a tuple ``(xbest, fbest)`` with the best position found, and the
    corresponding value ``fbest = f(xbest)``.


    """
    # Test function
    if not callable(f):
        raise ValueError('The argument `f` must be callable.')

    # Get problem dimension from p0
    d = len(p0)

    # First dimension of x and y must agree
    x = np.asarray(x)
    y = np.asarray(y)
    if x.shape[0] != y.shape[0]:
        raise ValueError(
            'The first dimension of `x` and `y` must be the same.')

    # Get number of points in data
    n = 1 / np.product(y.shape)

    # Check boundaries
    if not (boundaries is None or isinstance(boundaries, pints.Boundaries)):
        lower, upper = boundaries
        boundaries = pints.Boundaries(lower, upper)

    # Create an error measure
    class Err(pints.ErrorMeasure):
        def n_parameters(self):
            return d

        def __call__(self, p):
            return np.sum((y - f(x, *p))**2) * n

    # Set up optimisation
    e = Err()
    opt = pints.Optimisation(e, p0, boundaries=boundaries, method=method)

    # Set stopping criteria
    opt.set_threshold(threshold)
    opt.set_max_iterations(max_iter)
    opt.set_max_unchanged_iterations(max_unchanged)

    # Set parallelisation
    opt.set_parallel(parallel)

    # Set output
    opt.set_log_to_screen(True if verbose else False)

    # Run and return
    popt, fopt = opt.run()
    return popt


def fmin(f, x0, args=None, boundaries=None, threshold=None, max_iter=None,
         max_unchanged=200, verbose=False, parallel=False, method=None):
    """
    Minimises a callable function ``f``, starting from position ``x0``, using a
    :class:`pints.Optimiser`.

    Example:

        import pints

        def f(x):
            return (x[0] - 3) ** 2 + (x[1] + 5) ** 2

        xopt, fopt = pints.fmin(f, [1, 1])

    Arguments:

    ``f``
        A function or callable class to be minimised.
    ``x0``
        The initial point to search at. Must be a 1-dimensional sequence (e.g.
        a list or a numpy array).
    ``args``
        An optional tuple of extra arguments for ``f``.
    ``boundaries``
        An optional :class:`pints.Boundaries` object or a tuple
        ``(lower, upper)`` specifying lower and upper boundaries for the
        search. If no boundaries are provided an unbounded search is run.
    ``threshold``
        An optional absolute threshold stopping criterium.
    ``max_iter``
        An optional maximum number of iterations stopping criterium.
    ``max_unchanged=200``
        A stopping criterion based on the maximum number of successive
        iterations without a signficant change in ``f`` (see
        :meth:`pints.Optimisation`).
    ``verbose=False``
        Set to ``True`` to print progress messages to the screen.
    ``parallel=False``
        Allows parallelisation to be enabled.
        If set to ``True``, the evaluations will happen in parallel using a
        number of worker processes equal to the detected cpu core count. The
        number of workers can be set explicitly by setting ``parallel`` to an
        integer greater than 0.
    ``method``
        The :class:`pints.Optimiser` to use. If no method is specified,
        ``pints.CMAES`` is used.

    Returns a tuple ``(xbest, fbest)`` with the best position found, and the
    corresponding value ``fbest = f(xbest)``.
    """
    # Test function
    if not callable(f):
        raise ValueError('The argument `f` must be callable.')

    # Get problem dimension from x0
    d = len(x0)

    # Test extra arguments
    if args is not None:
        args = tuple(args)

    # Check boundaries
    if not (boundaries is None or isinstance(boundaries, pints.Boundaries)):
        lower, upper = boundaries
        boundaries = pints.Boundaries(lower, upper)

    # Create an error measure
    if args is None:

        class Err(pints.ErrorMeasure):
            def n_parameters(self):
                return d

            def __call__(self, x):
                return f(x)

    else:

        class Err(pints.ErrorMeasure):
            def n_parameters(self):
                return d

            def __call__(self, x):
                return f(x, *args)

    # Set up optimisation
    e = Err()
    opt = pints.Optimisation(e, x0, boundaries=boundaries, method=method)

    # Set stopping criteria
    opt.set_threshold(threshold)
    opt.set_max_iterations(max_iter)
    opt.set_max_unchanged_iterations(max_unchanged)

    # Set parallelisation
    opt.set_parallel(parallel)

    # Set output
    opt.set_log_to_screen(True if verbose else False)

    # Run and return
    return opt.run()

