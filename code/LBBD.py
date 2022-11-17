# -*- coding: utf-8 -*-
# @Time    : 2022/11/15 08:36
# @Author  : wangqianlong
# @email   ：17634233142@qq.com
# @FileName: LBBD.py

import time
import pandas as pd
from gurobipy import *

from parameters import *


class Master_Problem():
    def __init__(self):
        # 建立模型
        self.model = Model('MP')
        self.model.Params.MIPGap = 1e-8
        self.add_vars()
        self.set_objective()
        self.constraints()

    # 模型变量添加函数
    def add_vars(self):
        self.X = self.model.addVars(Sets['H'], Sets['D'], Sets['P'], vtype=GRB.BINARY, name='X')
        self.U = self.model.addVars(Sets['H'], Sets['D'], vtype=GRB.BINARY, name='U')
        self.Y = self.model.addVars(Sets['H'], Sets['D'], vtype=GRB.INTEGER, name='Y')
        self.W = self.model.addVars(Sets['P/P_prime'], vtype=GRB.BINARY, name='W')

    # 模型目标设置函数
    def set_objective(self):
        self.cost_suite = quicksum(list(hospitals[(hospitals['Hos'] == h) & (hospitals['d'] == d)]['Ghd'])[0] * self.U[h, d]
                                   for h in Sets['H'] for d in Sets['D'])
        self.cost_room = quicksum(list(hospitals[(hospitals['Hos'] == h) & (hospitals['d'] == d)]['Fhd'])[0] * self.Y[h, d]
                                  for h in Sets['H'] for d in Sets['D'])
        self.cost_3 = quicksum(parameters['k_1'] * patients.loc[p, 'HS'] * (d - patients.loc[p, 'NDE']) * self.X[h, d, p]
                               for h in Sets['H'] for d in Sets['D'] for p in Sets['P'])
        self.cost_4 = quicksum(parameters['k_2'] * patients.loc[p, 'HS'] * (len(Sets['D']) + 1 - patients.loc[p, 'NDE']) * self.W[p]
                               for p in Sets['P/P_prime'])
        # 模型添加目标
        self.objective = self.cost_suite + self.cost_room + self.cost_3 + self.cost_4
        self.model.setObjective(self.objective, GRB.MINIMIZE)

    def patient_be_planning(self):
        # cons_7 and cons_8
        for p in Sets['P']:
            if p in Sets['P_prime']:
                self.model.addConstr(quicksum(self.X[h, d, p] for h in Sets['H'] for d in Sets['D']) == 1,
                                     name=f'patient_be_planning{p}')
            else:
                self.model.addConstr(quicksum(self.X[h, d, p] for h in Sets['H'] for d in Sets['D']) + self.W[p] == 1,
                                     name=f'patient_be_planning_{p}')

    def availability_time_of_ors(self):
        # cons_10
        for h in Sets['H']:
            for d in Sets['D']:
                self.model.addConstr(quicksum(patients.loc[p, 'TBT'] * self.X[h, d, p] for p in Sets['P']) <=
                                     len(Sets['R']) * list(hospitals[(hospitals['Hos'] == h) & (hospitals['d'] == d)]['Bhd'])[0] * self.U[h, d],
                                     name=f'availability_time_of_ors_{h}_{d}')

    def cons_9_11_12_13(self):
        for h in Sets['H']:
            for d in Sets['D']:
                for p in Sets['P']:
                    self.model.addConstr(self.X[h, d, p] <= self.U[h, d],
                                         name=f'cons_9_{h}_{d}_{p}')
                    self.model.addConstr(patients.loc[p, 'TBT'] * self.X[h, d, p] <=
                                         list(hospitals[(hospitals['Hos'] == h) & (hospitals['d'] == d)]['Bhd'])[0],
                                         name=f'cons_11_{h}_{d}_{p}')
                self.model.addConstr(quicksum(patients.loc[p, 'TBT'] * self.X[h, d, p] for p in Sets['P']) <=
                                     list(hospitals[(hospitals['Hos'] == h) & (hospitals['d'] == d)]['Bhd'])[0] * self.Y[h, d],
                                     name=f'cons_12_{h}_{d}')
                self.model.addConstr(self.Y[h, d] <= len(Sets['R']),
                                     name=f'cons_13_{h}_{d}')

    def constraints(self):
        self.patient_be_planning()
        self.availability_time_of_ors()
        self.cons_9_11_12_13()

    def optimize_return(self):
        self.model.optimize()
        # 返回 Y 和 P
        self.MPS = {}
        if self.model.Status == 2:
            for h in Sets['H']:
                for d in Sets['D']:
                    self.MPS[(h, d)] = {
                        'Y': self.Y[h, d].X,
                        'P': [],
                    }
                    for p in Sets['P']:
                        if self.X[h, d, p].X >= 0.9:
                            self.MPS[(h, d)]['P'].append(p)
            return self.MPS
        else:
            return 'infeasible'


class Sub_Problem():
    def __init__(self, mps_sub_id, mps_sub):
        self.sub_id = mps_sub_id
        self.rooms = Sets['R']
        self.patients = mps_sub['P']
        self.Y_MPS = mps_sub['Y']
        # 建立模型
        self.model = Model('SP')
        self.model.Params.MIPGap = 1e-8
        self.add_vars()
        self.set_objective()
        self.constraints()

    def add_vars(self):
        self.X = self.model.addVars(self.patients, self.rooms, vtype=GRB.BINARY, name='X')
        self.Y = self.model.addVars(self.rooms, vtype=GRB.BINARY, name='Y')

    def set_objective(self):
        self.objective = quicksum(self.Y[r] for r in self.rooms)
        self.model.setObjective(self.objective, GRB.MINIMIZE)

    def constraints(self):
        for p in self.patients:
            self.model.addConstr(quicksum(self.X[p, r] for r in self.rooms) == 1, name=f'cons_14_{p}')
            for r in self.rooms:
                self.model.addConstr(self.X[p, r] <= self.Y[r], name=f'cons_16_{p}_{r}')

        for r in self.rooms:
            if r != 0:
                self.model.addConstr(self.Y[r] <= self.Y[r - 1], name=f'cons_17_{r}')
            self.model.addConstr(quicksum(patients.loc[p, 'TBT'] * self.X[p, r] for p in self.patients) <=
                                 list(hospitals[(hospitals['Hos'] == self.sub_id[0]) & (hospitals['d'] == self.sub_id[1])]['Bhd'])[0] * self.Y[r],
                                 name=f'cons_15_{r}')

    def optimize_return(self):
        self.model.optimize()
        self.SPS = {}
        if self.model.Status == 2:
            for r in self.rooms:
                if self.Y[r].X >= 0.9:
                    self.SPS[r] = []
                    for p in self.patients:
                        if self.X[p, r].X >= 0.9:
                            self.SPS[r].append(p)
            return [self.model.objVal, self.SPS]
        else:
            return [None, 'infeasible']


def add_benders_cut(mp, sps, iter):
    add_cut_num = 0
    lbbd = 2
    for sub_id in sps.keys():
        if sps[sub_id]:
            if sps[sub_id]['solution'][0] is None:
                if lbbd == 1:
                    mp.model.addConstr(quicksum((1 - mp.X[sub_id[0], sub_id[1], p]) for p in sps[sub_id]['model'].patients) >= 1,
                                       name=f'feasibility_cut_{iter}_{sub_id[0]}_{sub_id[1]}')
                elif lbbd == 2:
                    mp.model.addConstr(mp.Y[sub_id[0], sub_id[1]] + quicksum((1 - mp.X[sub_id[0], sub_id[1], p]) for p in sps[sub_id]['model'].patients)
                                       >= len(Sets['R']) + 1,
                                       name=f'feasibility_cut_{iter}_{sub_id[0]}_{sub_id[1]}')
                elif lbbd == 3:
                    mp.model.addConstr(mp.Y[sub_id[0], sub_id[1]] + quicksum(
                        (1 - mp.X[sub_id[0], sub_id[1], p]) for p in sps[sub_id]['model'].patients)
                                       >= sps[sub_id]['model'].Y_MPS + 1,
                                       name=f'feasibility_cut_{iter}_{sub_id[0]}_{sub_id[1]}')
                add_cut_num += 1
            else:
                if sps[sub_id]['solution'][0] != mp.MPS[sub_id]['Y']:
                    mp.model.addConstr(mp.Y[sub_id[0], sub_id[1]] + quicksum(1 - mp.X[sub_id[0], sub_id[1], p] for p in sps[sub_id]['model'].patients)
                                       >= sps[sub_id]['solution'][0],
                                       name=f'optimality_cut_{iter}_{sub_id[0]}_{sub_id[1]}')
                    add_cut_num += 1
    return add_cut_num


def LBBD(MP, max_iter):
    # initial
    MPS = MP.optimize_return()
    SPSS, MPSS, UPPER_BOUND = [], [MPS], []
    add_cut_num_all = 0
    for iter in range(max_iter):
        sub_problems = {}
        for sub_id, sub_yp in MPS.items():
            sub_problems[sub_id] = {}
            if sub_yp['Y'] >= 0.5:
                sub_problems[sub_id]['model'] = Sub_Problem(sub_id, sub_yp)
                sub_problems[sub_id]['solution'] = sub_problems[sub_id]['model'].optimize_return()
        SPSS.append(sub_problems)
        add_cut_num = add_benders_cut(MP, sub_problems, iter)
        add_cut_num_all += add_cut_num
        print(f'------------------------ iter: {iter}, add_cut_num: {add_cut_num} --------------------------')
        if add_cut_num == 0:
            print('-------------------------------- optimal -----------------------------------')
            print(f'--------------------------- add_cut_num_all: {add_cut_num_all} ---------------------------')
            break
        MPS = MP.optimize_return()
        MPSS.append(MPS)
    MP.model.write('MP_model.lp')
    return MPSS, SPSS


# 初始化数据
n_patient, n_or, instance_id = 20, 3, 11
patients = pd.read_csv(f'../data/patients_{n_patient}_{instance_id}.csv', index_col=0)
hospitals = pd.read_csv(f'../data/hospitals.csv')

Sets = {
    'P': list(patients.index),
    'P_prime': list(patients[patients['Type'] == 1].index),
    'H': [h for h in range(parameters['hospital'])],
    'D': [d for d in range(parameters['day'])],
    'R': [r for r in range(n_or)],
}

Sets['P/P_prime'] = list(set(Sets['P']).difference(set(Sets['P_prime'])))

MP = Master_Problem()
t_1 = time.time()
MPSS, SPSS = LBBD(MP, 1600)
t_2 = time.time()
print(f'LBBD: optimal objective: {MP.objective.getValue()}')
print(f'LBBD time: {t_2 - t_1}')

# for p in Sets['P']:
#     MP.model.addConstr(MP.X[0, 0, p] == 1, name=f'patient_{p}')
#
# MPS = MP.optimize_return()
# MP.model.computeIIS()
# MP.model.write('LBBD_model.ilp')
