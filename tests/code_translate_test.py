from __future__ import print_function

import base64
import multiprocessing
import os
import pickle
import string
import subprocess
import sys
import tempfile
import textwrap
import traceback
import unittest
import uuid

import pytest
import six

from cloudpickle import dumps, loads

if sys.version < '3':
    PY27 = sys.version_info[:2] == (2, 7)
    PY3 = False
else:
    PY27 = False
    PY3 = True

if 'PY26_EXECUTABLE' in os.environ:
    PY26_EXECUTABLE = string.Template(os.environ['PY26_EXECUTABLE']).substitute(os.environ)
else:
    PY26_EXECUTABLE = None

if 'PY37_EXECUTABLE' in os.environ:
    PY37_EXECUTABLE = string.Template(os.environ['PY37_EXECUTABLE']).substitute(os.environ)
else:
    PY37_EXECUTABLE = None

try:
    import numpy
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# if bytecode needed in debug, switch it on
DUMP_CODE = False

CROSS_VAR_PICKLE_CODE = """
from __future__ import absolute_import

import base64
import json
import sys
import platform
import os
import pickle

import six

try:
    os.unlink(os.path.realpath(__file__))
except Exception:
    pass

from cloudpickle import dumps
from {module_name} import {method_ref}


def to_text(binary, encoding='utf-8'):
    if binary is None:
        return binary
    if isinstance(binary, (six.binary_type, bytearray)):
        return binary.decode(encoding)
    elif isinstance(binary, six.text_type):
        return binary
    else:
        return str(binary) if six.PY3 else str(binary).decode(encoding)


def to_binary(text, encoding='utf-8'):
    if text is None:
        return text
    if isinstance(text, six.text_type):
        return text.encode(encoding)
    elif isinstance(text, (six.binary_type, bytearray)):
        return bytes(text)
    else:
        return str(text).encode(encoding) if six.PY3 else str(text)


def to_str(text, encoding='utf-8'):
    return to_text(text, encoding=encoding) if six.PY3 else to_binary(text, encoding=encoding)
    

client_impl = (sys.version_info[0],
               sys.version_info[1],
               platform.python_implementation().lower())
result_obj = {method_ref}()
result_tuple = (
    base64.b64encode(dumps(result_obj, dump_code={dump_code})),
    client_impl,
)
with open(r'{pickled_file}', 'w') as f:
    f.write(to_str(base64.b64encode(pickle.dumps(result_tuple, protocol=0))))
    f.close()
""".replace('{module_name}', __name__).replace('{dump_code}', repr(DUMP_CODE))


def to_binary(text, encoding='utf-8'):
    if text is None:
        return text
    if isinstance(text, six.text_type):
        return text.encode(encoding)
    elif isinstance(text, (six.binary_type, bytearray)):
        return bytes(text)
    else:
        return str(text).encode(encoding) if six.PY3 else str(text)


def pickled_runner(q, pickled, args, kwargs, **kw):
    try:
        wrapper = kw.pop('wrapper', None)
        impl = kwargs.pop('impl', None)
        if wrapper:
            wrapper = loads(wrapper)
        else:
            wrapper = lambda v, a, kw: v(*a, **kw)
        deserial = loads(base64.b64decode(pickled), impl=impl, dump_code=DUMP_CODE)
        q.put(wrapper(deserial, args, kwargs))
    except:
        traceback.print_exc()
        raise


def run_pickled(pickled, *args, **kwargs):
    pickled, kwargs['impl'] = pickle.loads(base64.b64decode(pickled))
    wrapper_kw = {}
    if 'wrapper' in kwargs:
        wrapper_kw['wrapper'] = dumps(kwargs.pop('wrapper'))
    queue = multiprocessing.Queue()
    proc = multiprocessing.Process(target=pickled_runner, args=(queue, pickled, args, kwargs), kwargs=wrapper_kw)
    proc.start()
    proc.join()
    if proc.exitcode != 0:
        raise RuntimeError('Pickle process exited abnormally.')
    try:
        return queue.get()
    except:
        return None


def _gen_nested_yield_obj():
    out_closure = 10

    class _NestClass(object):
        inner_gain = 5

        def __init__(self):
            self._o_closure = out_closure

        def nested_method(self, add_val):
            if add_val < 5:
                return self._o_closure + add_val * 2 + self.inner_gain
            else:
                return self._o_closure + add_val + self.inner_gain

    class _FuncClass(object):
        def __init__(self):
            self.nest = _NestClass()

        def __call__(self, add_val):
            yield self.nest.nested_method(add_val)

    return _FuncClass


class BuildMeta(type):
    pass


class BuildBase(object):
    pass


if not PY3:
    def _gen_class_builder_func():
        out_closure = 10

        def _gen_nested_class_obj():
            class BuildCls(BuildBase):
                __metaclass__ = BuildMeta
                a = out_closure

                def b(self, add_val):
                    print(self.a)
                    return self.a + add_val + out_closure

            return BuildCls
        return _gen_nested_class_obj
else:
    py3_code = textwrap.dedent("""
    def _gen_class_builder_func():
        out_closure = 10

        def _gen_nested_class_obj():
            class BuildCls(BuildBase, metaclass=BuildMeta):
                a = out_closure

                def b(self, add_val):
                    print(self.a)
                    return self.a + add_val + out_closure

            return BuildCls
        return _gen_nested_class_obj
    """)
    my_locs = locals().copy()
    six.exec_(py3_code, globals(), my_locs)
    _gen_class_builder_func = my_locs.get('_gen_class_builder_func')


if sys.version_info[:2] < (3, 6):
    def _gen_format_string_func():
        out_closure = 4.0

        def _format_fun(arg):
            return 'Formatted stuff {0}: {1:>5}'.format(arg, out_closure)

        return _format_fun
else:
    py36_code = textwrap.dedent("""
    def _gen_format_string_func():
        out_closure = 4.0

        def _format_fun(arg):
            return f'Formatted stuff {arg}: {out_closure:>5}'

        return _format_fun
    """)
    my_locs = locals().copy()
    six.exec_(py36_code, globals(), my_locs)
    _gen_format_string_func = my_locs.get('_gen_format_string_func')


if sys.version_info[:2] < (3, 6):
    def _gen_build_unpack_func():
        out_closure = (1, 2, 3)

        def merge_kws(a, b, *args, **kwargs):
            kwargs.update(dict(a=a, b=b))
            kwargs.update((str(idx), v) for idx, v in enumerate(args))
            return kwargs

        def _gen_fun(arg):
            t = out_closure + (4, ) + (5, 6, 7) + (arg, )
            l = list(out_closure) + [4, ] + [5, 6, 7]
            s = set(out_closure) | set([4]) | set([5, 6, 7])
            m = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5}
            wk = merge_kws(3, 4, 5, *(out_closure + (1, 2, 3)), **dict(m=1, n=2, p=3, q=4, r=5))
            return t, l, s, m, wk

        return _gen_fun
else:
    py36_code = textwrap.dedent("""
    def _gen_build_unpack_func():
        out_closure = (1, 2, 3)

        def merge_kws(a, b, *args, **kwargs):
            kwargs.update(dict(a=a, b=b))
            kwargs.update((str(idx), v) for idx, v in enumerate(args))
            return kwargs

        def _gen_fun(arg):
            t = (*out_closure, *(4, ), *(5, 6, 7), *(arg, ))
            l = [*out_closure, *(4, ), *[5, 6, 7]]
            s = {*out_closure, *[4], *[5, 6, 7]}
            m = {**dict(a=1, b=2), **dict(c=3), **dict(d=4, e=5)}
            wk = merge_kws(3, 4, 5, *out_closure, *[1, 2, 3], **dict(m=1, n=2), **dict(p=3, q=4, r=5))
            return t, l, s, m, wk

        return _gen_fun
    """)
    my_locs = locals().copy()
    six.exec_(py36_code, globals(), my_locs)
    _gen_build_unpack_func = my_locs.get('_gen_build_unpack_func')


if sys.version_info[:2] < (3, 6):
    def _gen_matmul_func():
        out_closure = [[4, 9, 2], [3, 5, 7], [8, 1, 6]]

        def _gen_fun(arg):
            import numpy as np
            a = np.array(out_closure)
            b = np.array([9, 5, arg])
            c = np.dot(a, b)
            return repr(c)

        return _gen_fun
else:
    py36_code = textwrap.dedent("""
    def _gen_matmul_func():
        out_closure = [[4, 9, 2], [3, 5, 7], [8, 1, 6]]

        def _gen_fun(arg):
            import numpy as np
            a = np.array(out_closure)
            b = np.array([9, 5, arg])
            c = a @ b
            return repr(c)

        return _gen_fun
    """)
    my_locs = locals().copy()
    six.exec_(py36_code, globals(), my_locs)
    _gen_matmul_func = my_locs.get('_gen_matmul_func')


def _gen_try_except_func():
    out_closure = dict(k=12.0)

    def _gen_fun(arg):
        ex = None
        agg = arg

        def _cl():
            print(ex)

        try:
            agg *= out_closure['not_exist']
        except KeyError as ex:
            agg += 1

        try:
            agg -= out_closure['k']
        except KeyError as ex:
            _cl()
            agg /= 10
        return agg

    return _gen_fun


def _gen_nested_fun():
    out_closure = 10

    def _gen_nested_obj():
        # class NestedClass(object):
        def nested_method(add_val):
            return out_closure + add_val

        return nested_method

    return lambda v: _gen_nested_obj()(*(v, ))


class Test(unittest.TestCase):
    @staticmethod
    def _invoke_other_python_pickle(executable, method_ref):
        if callable(method_ref):
            method_ref = method_ref.__name__
        ts_name = os.path.join(tempfile.gettempdir(), 'pyodps_pk_cross_test_{0}.py'.format(str(uuid.uuid4())))
        tp_name = os.path.join(tempfile.gettempdir(), 'pyodps_pk_cross_pickled_{0}'.format(str(uuid.uuid4())))
        script_text = CROSS_VAR_PICKLE_CODE.format(method_ref=method_ref, pickled_file=tp_name)
        with open(ts_name, 'w') as out_file:
            out_file.write(script_text)
            out_file.close()
        proc = subprocess.Popen([executable, ts_name], cwd=os.getcwd())
        proc.wait()
        if not os.path.exists(tp_name):
            raise RuntimeError('Pickle error occured!')
        else:
            with open(tp_name, 'r') as f:
                pickled = f.read().strip()
                f.close()
            os.unlink(tp_name)

            if not pickled:
                raise RuntimeError('Pickle error occured!')
        return pickled

    def test_nested_func(self):
        func = _gen_nested_fun()
        obj_serial = base64.b64encode(dumps(func))
        deserial = loads(base64.b64decode(obj_serial))
        self.assertEqual(deserial(20), func(20))

    @pytest.mark.skipif(not PY27, reason='Ignored under Python 3')
    @pytest.mark.skipif(PY37_EXECUTABLE is None, reason='Python 3 interpreter not specified')
    def test_3to2_format_string(self):
        func = _gen_format_string_func()
        py3_serial = to_binary(self._invoke_other_python_pickle(PY37_EXECUTABLE, _gen_format_string_func))
        self.assertEqual(run_pickled(py3_serial, 20), func(20))

    @pytest.mark.skipif(not PY27, reason='Ignored under Python 3')
    @pytest.mark.skipif(PY37_EXECUTABLE is None, reason='Python 3 interpreter not specified')
    def test_3to2_build_unpack(self):
        func = _gen_build_unpack_func()
        py3_serial = to_binary(self._invoke_other_python_pickle(PY37_EXECUTABLE, _gen_build_unpack_func))
        self.assertEqual(run_pickled(py3_serial, 20), func(20))

    @pytest.mark.skipif(not PY27, reason='Ignored under Python 3')
    @pytest.mark.skipif(PY37_EXECUTABLE is None, reason='Python 3 interpreter not specified')
    @pytest.mark.skipif(not HAS_NUMPY, reason='Ignored when no numpy is installed')
    def test_3to2_matmul(self):
        func = _gen_matmul_func()
        py3_serial = to_binary(self._invoke_other_python_pickle(PY37_EXECUTABLE, _gen_matmul_func))
        self.assertEqual(run_pickled(py3_serial, 20), func(20))

    @pytest.mark.skipif(not PY27, reason='Ignored under Python 3')
    @pytest.mark.skipif(PY37_EXECUTABLE is None, reason='Python 3 interpreter not specified')
    def test_3to2_try_except(self):
        func = _gen_try_except_func()
        py3_serial = to_binary(self._invoke_other_python_pickle(PY37_EXECUTABLE, _gen_try_except_func))
        self.assertEqual(run_pickled(py3_serial, 20), func(20))

    @pytest.mark.skipif(not PY27, reason='Ignored under Python 3')
    @pytest.mark.skipif(PY37_EXECUTABLE is None, reason='Python 3 interpreter not specified')
    def test_3to2_nested_func(self):
        func = _gen_nested_fun()
        py3_serial = to_binary(self._invoke_other_python_pickle(PY37_EXECUTABLE, _gen_nested_fun))
        self.assertEqual(run_pickled(py3_serial, 20), func(20))

    def test_nested_class_obj(self):
        func = _gen_nested_yield_obj()
        obj_serial = base64.b64encode(dumps(func))
        deserial = loads(base64.b64decode(obj_serial))
        self.assertEqual(sum(deserial()(20)), sum(func()(20)))

    @pytest.mark.skipif(not PY27, reason='Only runnable under Python 2.7')
    @pytest.mark.skipif(PY37_EXECUTABLE is None, reason='Python 3 interpreter not specified')
    def test_3to27_nested_yield_obj(self):
        func = _gen_nested_yield_obj()
        py3_serial = to_binary(self._invoke_other_python_pickle(PY37_EXECUTABLE, _gen_nested_yield_obj))
        self.assertEqual(run_pickled(py3_serial, 20, wrapper=lambda fun, a, kw: sum(fun()(*a, **kw))),
                         sum(func()(20)))

    @pytest.mark.skipif(not PY27, reason='Only runnable under Python 2.7')
    @pytest.mark.skipif(PY26_EXECUTABLE is None, reason='Python 2.6 interpreter not specified')
    def test_26to27_nested_yield_obj(self):
        func = _gen_nested_yield_obj()
        py26_serial = to_binary(self._invoke_other_python_pickle(PY26_EXECUTABLE, _gen_nested_yield_obj))
        self.assertEqual(run_pickled(py26_serial, 20, wrapper=lambda fun, a, kw: sum(fun()(*a, **kw))),
                         sum(func()(20)))

    @pytest.mark.skipif(not PY27, reason='Only runnable under Python 2.7')
    @pytest.mark.skipif(PY37_EXECUTABLE is None, reason='Python 3 interpreter not specified')
    def test_3to27_nested_class_obj(self):
        cls = _gen_class_builder_func()()
        py3_serial = to_binary(self._invoke_other_python_pickle(PY37_EXECUTABLE, _gen_class_builder_func))
        self.assertEqual(run_pickled(py3_serial, 5, wrapper=lambda cls, a, kw: cls()().b(*a, **kw)),
                         cls().b(5))
