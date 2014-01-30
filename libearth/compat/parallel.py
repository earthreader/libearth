""":mod:`libearth.compat.parallel` --- Threading-related compatibility layer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. function:: cpu_count()

   Get the number of CPU cores.

   :returns: the number of cpu cores
   :rtype: :class:`numbers.Integral`

.. function:: parallel_map(pool_size, function, iterable, *iterables)

   Parallel vesion of builtin :func:`map()` except of some differences:

   - It takes a more argument at first: ``pool_size``.
   - The function applications will be done in parallel.
   - The order of arguments to results are not maintained.
     You should treat these as a set.
   - The result is a lazy iterable.  Although the function immediately returns
     an iterable, it might block if some results are not completely ready
     when it's iterated.

   :param pool_size: the number of workers
   :type pool_size: :class:`numbers.Integral`
   :param function: the function to apply iterables as its arguments
   :type function: :class:`collections.Callable`
   :param iterable: function argument values
   :type iterable: :class:`collections.Iterable`
   :returns: a promise iterable to future results
   :rtype: :class:`collections.Iterable`

   .. versionchanged:: 0.1.1
      Errored values are raised at the lastest.

"""
import collections
import numbers
import sys

from . import IRON_PYTHON, PY3

__all__ = 'cpu_count', 'parallel_map'


if IRON_PYTHON:
    from System import Environment

    def cpu_count():
        return Environment.ProcessorCount
else:
    import multiprocessing

    def cpu_count():
        try:
            return multiprocessing.cpu_count()
        except NotImplementedError:
            return 1


try:
    from concurrent.futures import ThreadPoolExecutor
except ImportError:
    if IRON_PYTHON:
        from System import Action
        from System.Collections.Concurrent import BlockingCollection
        from System.Collections.Generic import IEnumerable
        from System.Threading import Thread, ThreadStart
        from System.Threading.Tasks import Parallel, ParallelOptions

        class parallel_map(collections.Iterable):

            ForEach = Parallel.ForEach[object].Overloads[
                IEnumerable[object],
                ParallelOptions,
                Action[object]
            ]

            def __init__(self, pool_size, function, *iterables):
                if not isinstance(pool_size, numbers.Integral):
                    raise TypeError('pool_size must be an integer, not ' +
                                    repr(pool_size))
                elif not callable(function):
                    raise TypeError('function must be callable, not ' +
                                    repr(function))
                elif not iterables:
                    raise TypeError('missing iterable')
                self.function = function
                self.results = BlockingCollection[tuple]()
                args = zip(*iterables)
                self.length = len(args)
                options = ParallelOptions()
                options.MaxDegreeOfParallelism = pool_size
                Thread.__new__.Overloads[ThreadStart](
                    Thread,
                    lambda: self.ForEach(args, options, self.store_result)
                ).Start()

            def store_result(self, args):
                try:
                    value = self.function(*args)
                except Exception as e:
                    result = None, e
                else:
                    result = value, None
                self.results.Add(result)

            def __iter__(self):
                errors = []
                for _ in xrange(self.length):
                    value, error = self.results.Take()
                    if error is None:
                        yield value
                    else:
                        errors.append(error)
                for error in errors:
                    raise error
    else:
        from multiprocessing.pool import ThreadPool

        class parallel_map(collections.Iterable):

            def __init__(self, pool_size, function, *iterables):
                if not isinstance(pool_size, numbers.Integral):
                    raise TypeError('pool_size must be an integer, not ' +
                                    repr(pool_size))
                elif not callable(function):
                    raise TypeError('function must be callable, not ' +
                                    repr(function))
                elif not iterables:
                    raise TypeError('missing iterable')
                self.pool = ThreadPool(pool_size)
                self.function = function
                self.results = self.pool.imap_unordered(self.map_function,
                                                        zip(*iterables))

            def map_function(self, args):
                try:
                    value = self.function(*args)
                except Exception:
                    return False, sys.exc_info()
                return True, value

            def __iter__(self):
                errors = []
                for success, value in self.results:
                    if success:
                        yield value
                    else:
                        errors.append(value)
                self.pool.close()
                self.pool.join()
                for error in errors:
                    exec('raise error[1], None, error[2]')
else:
    class parallel_map(collections.Iterable):

        def __init__(self, pool_size, function, *iterables):
            if not isinstance(pool_size, numbers.Integral):
                raise TypeError('pool_size must be an integer, not ' +
                                repr(pool_size))
            elif not callable(function):
                raise TypeError('function must be callable, not ' +
                                repr(function))
            elif not iterables:
                raise TypeError('missing iterable')
            self.pool = ThreadPoolExecutor(pool_size)
            self.function = function
            self.results = self.pool.map(self.map_function, *iterables)

        def map_function(self, *args):
            try:
                value = self.function(*args)
            except Exception:
                return False, sys.exc_info()
            return True, value

        def __iter__(self):
            errors = []
            for success, value in self.results:
                if success:
                    yield value
                else:
                    errors.append(value)
            self.pool.shutdown()
            if PY3:
                for _, exc, tb in errors:
                    raise exc.with_traceback(tb)
            else:
                for _, exc, tb in errors:
                    exec('raise exc, None, tb')
