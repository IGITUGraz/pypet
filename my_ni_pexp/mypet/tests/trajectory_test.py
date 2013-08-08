

__author__ = 'robert'



import numpy as np
import unittest
from mypet.parameter import Parameter, SparseParameter, SimpleResult
from mypet.trajectory import Trajectory, SingleRun
from mypet.storageservice import LazyStorageService
from mypet.utils.explore import identity
import pickle
import logging
import cProfile
import scipy.sparse as spsp
import mypet.petexceptions as pex
import multiprocessing as multip

import mypet.storageservice as stsv

class ImAParameterInDisguise(Parameter):
    pass

class ImAResultInDisguise(SimpleResult):
    pass

class TrajectoryTest(unittest.TestCase):


    def setUp(self):
        name = 'Moop'

        self.traj = Trajectory(name,[ImAParameterInDisguise])

        comment = 'This is a comment'
        self.traj.add_comment(comment)

        self.assertTrue(comment == self.traj.get_comment())

        self.traj.add_parameter('IntParam',0,1,2,3)
        sparsemat = spsp.csr_matrix((1000,1000))
        sparsemat[1,2] = 17.777

        self.traj.add_parameter('SparseParam', sparsemat, param_type=SparseParameter)

        self.traj.add_parameter('FloatParam')

        self.traj.adp(Parameter('FortyTwo', 42))

        self.traj.add_result('Im.A.Simple.Result',44444,result_type=SimpleResult)

        self.traj.FloatParam=[1.0,2.0,3.0]

        self.traj.explore(identity,{self.traj.FloatParam.gfn('val0'):[1.0,1.1,1.2,1.3]})

        self.assertTrue(len(self.traj) == 4)



        with self.assertRaises(AttributeError):
            self.traj.ap('Peter.  h ._hurz')



    def testGet(self):
        self.traj.set_fast_access(True)
        self.traj.get('FloatParam', fast_access=True) == self.traj.FloatParam

        self.traj.set_fast_access(False)

        self.traj.get('FloatParam').val == self.traj.Par.FloatParam.return_default()

        self.traj.FortyTwo.val == 42


    def testremove(self):
        self.traj.remove(self.traj.FloatParam)

        with self.assertRaises(AttributeError):
            self.traj.FloatParam

        self.assertFalse('FloatParam' in self.traj.to_dict())

        self.assertTrue(len(self.traj)==1)

        self.traj.remove('FortyTwo')

        self.traj.remove('SparseParam')
        self.traj.remove('IntParam')

        self.assertTrue(len(self.traj)==0)

    def test_changing(self):

        self.traj.change_config('testconf', 1)
        self.traj.change_parameter('testparam', 1)
        self.traj.change_parameter('I_do_not_exist', 2)

        self.traj.ap('testparam', 0)
        self.traj.ac('testconf', 0)

        self.traj.set_fast_access(True)

        self.assertTrue(self.traj.testparam == 1)
        self.assertTrue(self.traj.testconf == 1)

        ### should raise an error because 'I_do_not_exist', does not exist:
        with self.assertRaises(pex.DefaultReplacementError):
            self.traj.prepare_experiment()


    def test_if_pickable(self):

        self.traj.set_fast_access(True)
        self.traj.set_storage_service(stsv.HDF5QueueStorageServiceSender())

        dump = pickle.dumps(self.traj)

        newtraj = pickle.loads(dump)


        self.assertTrue(len(newtraj) == len(self.traj))


        for key, val in self.traj.to_dict(fast_access=True).items():
            val = newtraj.get(key)

    def test_dynamic_class_loading(self):
        self.traj.add_parameter('Rolf', 1.8,param_type = ImAParameterInDisguise, )

    def test_standard_change_param_change(self):
        self.traj.set_standard_param_type(ImAParameterInDisguise)

        self.traj.ap('I.should_be_not.normal')

        self.assertIsInstance(self.traj.normal, ImAParameterInDisguise)

        self.traj.set_standard_result_type(ImAResultInDisguise)

        self.traj.add_result('Peter.Parker')

        self.assertIsInstance(self.traj.Parker, ImAResultInDisguise)

class SingleRunTest(unittest.TestCase):


    def setUp(self):

        logging.basicConfig(level = logging.INFO)
        traj = Trajectory('Test')

        traj.set_storage_service(LazyStorageService())

        large_amount = 111

        for irun in range(large_amount):
            name = 'There.Are.Many.Parameters.Like.Me' + str(irun)

            traj.ap(name,value = irun)


        traj.ap('TestExplorer', value=1)

        traj.explore(identity,{traj.TestExplorer.gfn('value'):[1,2,3,4,5]})

        self.traj = traj
        self.n = 1
        self.single_run = self.traj.make_single_run(self.n)
        self.assertTrue(len(self.single_run)==1)



    def test_if_single_run_can_be_pickled(self):

        self.single_run._storageservice=stsv.HDF5QueueStorageServiceSender()
        dump = pickle.dumps(self.single_run)

        single_run_rec = pickle.loads(dump)

        #print single_run.get('Test').val

        elements_dict = self.single_run.to_dict()
        for key in elements_dict:
            val = self.single_run.get(key,fast_access=True)
            val_rec = single_run_rec.get(key).val
            self.assertTrue(np.all(val==val_rec))



    def test_adding_derived_parameter_and_result(self):
        value = 44.444
        self.single_run.add_derived_parameter('Im.A.Nice.Guy.Yo', value)
        self.assertTrue(self.single_run.Nice.Yo.val == value)

        self.single_run.add_result('Puberty.Hacks', value)
        resval= self.single_run.Hacks.val
        self.assertTrue(resval == value)


    def test_standard_change_param_change(self):
        self.single_run.set_standard_param_type(ImAParameterInDisguise)

        self.single_run.ap('I.should_be_not.normal')

        self.assertIsInstance(self.single_run.normal, ImAParameterInDisguise)

        self.single_run.set_standard_result_type(ImAResultInDisguise)

        self.single_run.add_result('Peter.Parker')

        self.assertIsInstance(self.single_run.Parker, ImAResultInDisguise)

class SingleRunQueueTest(unittest.TestCase):


    def setUp(self):

        logging.basicConfig(level = logging.INFO)
        traj = Trajectory('Test')

        traj.set_storage_service(LazyStorageService())

        large_amount = 111

        for irun in range(large_amount):
            name = 'There.Are.Many.Parameters.Like.Me' + str(irun)

            traj.ap(name,value = irun)


        traj.ap('TestExplorer', value=1)

        traj.explore(identity,{traj.TestExplorer.gfn('value'):[1,2,3,4,5]})

        self.traj = traj
        self.n = 1
        self.single_run = self.traj.make_single_run(self.n)
        self.assertTrue(len(self.single_run)==1)


    def test_queue(self):

        manager = multip.Manager()
        queue = manager.Queue()

        to_put = ('msg',[self.single_run],{})

        queue.put(to_put)

        pass


if __name__ == '__main__':
    unittest.main()