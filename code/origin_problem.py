# -*- coding: utf-8 -*-
# @Time    : 2022/11/14 16:57
# @Author  : wangqianlong
# @email   ：17634233142@qq.com
# @FileName: origin_problem.py

import time
import pandas as pd
from gurobipy import *

from parameters import *


# 初始化模型参数函数
def model_initial_parameter(model):
    model.Params.TimeLimit = 3600
    model.Params.MIPGap = 1e-8


# 模型变量添加函数
def add_vars(model):
    X = model.addVars(Sets['H'], Sets['D'], Sets['P'], Sets['R'], vtype=GRB.BINARY, name='X')
    U = model.addVars(Sets['H'], Sets['D'], vtype=GRB.BINARY, name='U')
    Y = model.addVars(Sets['H'], Sets['D'], Sets['R'], vtype=GRB.BINARY, name='Y')
    W = model.addVars(Sets['P/P_prime'], vtype=GRB.BINARY, name='W')
    return X, U, Y, W


# 模型目标设置函数
def set_objective(model, X, U, Y, W):
    cost_suite = quicksum(list(hospitals[(hospitals['Hos'] == h) & (hospitals['d'] == d)]['Ghd'])[0] * U[h, d]
                          for h in Sets['H'] for d in Sets['D'])
    cost_room = quicksum(list(hospitals[(hospitals['Hos'] == h) & (hospitals['d'] == d)]['Fhd'])[0] * Y[h, d, r]
                         for h in Sets['H'] for d in Sets['D'] for r in Sets['R'])
    cost_3 = quicksum(parameters['k_1'] * patients.loc[p, 'HS'] * (d - patients.loc[p, 'NDE']) * X[h, d, p, r]
                      for h in Sets['H'] for d in Sets['D'] for p in Sets['P'] for r in Sets['R'])
    cost_4 = quicksum(parameters['k_2'] * patients.loc[p, 'HS'] * (len(Sets['D']) + 1 - patients.loc[p, 'NDE']) * W[p]
                      for p in Sets['P/P_prime'])
    # 模型添加目标
    objective = cost_suite + cost_room + cost_3 + cost_4
    model.setObjective(objective, GRB.MINIMIZE)
    return objective, cost_suite, cost_room, cost_3, cost_4


def patient_be_planning(model, X, W):
    # cons_1 and cons_2
    for p in Sets['P']:
        if p in Sets['P_prime']:
            model.addConstr(quicksum(X[h, d, p, r] for h in Sets['H'] for d in Sets['D'] for r in Sets['R']) == 1,
                            name=f'patient_be_planning{p}')
        else:
            model.addConstr(quicksum(X[h, d, p, r] for h in Sets['H'] for d in Sets['D'] for r in Sets['R']) + W[p] == 1,
                            name=f'patient_be_planning_{p}')


def availability_time_of_ors(model, X, Y):
    for h in Sets['H']:
        for d in Sets['D']:
            for r in Sets['R']:
                model.addConstr(quicksum(patients.loc[p, 'TBT'] * X[h, d, p, r] for p in Sets['P']) <=
                                list(hospitals[(hospitals['Hos'] == h) & (hospitals['d'] == d)]['Bhd'])[0] * Y[h, d, r],
                                name=f'availability_time_of_ors_{h}_{d}_{r}')


def cons_4_5_6(model, X, Y, U):
    for h in Sets['H']:
        for d in Sets['D']:
            for r in Sets['R']:
                if r != 0:
                    model.addConstr(Y[h, d, r] <= Y[h, d, r - 1], name=f'cons_4_{h}_{d}_{r}')
                model.addConstr(Y[h, d, r] <= U[h, d], name=f'cons_5_{h}_{d}_{r}')
                for p in Sets['P']:
                    model.addConstr(X[h, d, p, r] <= Y[h, d, r], f'cons_6_{h}_{d}_{p}_{r}')


def constraints(model, X, U, Y, W):
    patient_be_planning(model, X, W)
    availability_time_of_ors(model, X, Y)
    cons_4_5_6(model, X, Y, U)


def output(X, Y, W):
    for d in Sets['D']:
        for h in Sets['H']:
            for r in Sets['R']:
                if Y[h, d, r].X >= 0.9:
                    print(f'Day-Hospital-Room: {d}-{h}-{r}, Patient: ', end='')
                    for p in Sets['P']:
                        if X[h, d, p, r].X >= 0.9:
                            print(p, end=', ')
                    print('')
    print('Not Scheduled Patients: ', end='')
    for p in Sets['P/P_prime']:
        if W[p].X >= 0.9:
            print(p, end=', ')


if __name__ == '__main__':
    # 初始化数据
    n_patient, n_or, instance_id = 40, 5, 3
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

    # 建立模型
    model = Model('model')
    # 模型参数初始化
    model_initial_parameter(model)
    # 添加模型变量
    X, U, Y, W = add_vars(model)
    # 设置模型求解目标
    objective, cost_suite, cost_room, cost_3, cost_4 = set_objective(model, X, U, Y, W)
    # 添加模型约束
    constraints(model, X, U, Y, W)
    # 求解
    t_s = time.time()
    model.optimize()
    t_e = time.time()
    # 输出
    if model.Status == 3:
        print('约束冲突')
        # 输出约束冲突内容
        model.computeIIS()
        model.write('model.ilp')
    elif model.Status == 2:
        best_value = model.objVal
        output(X, Y, W)
        print('cost_suite: ', cost_suite.getValue())
        print('cost_room: ', cost_room.getValue())
        print('cost_3: ', cost_3.getValue())
        print('cost_4: ', cost_4.getValue())
        print('objective: ', best_value, '\ntime: ', t_e - t_s)
        # 输出lp文件
        model.write('model.lp')
    elif model.Status == 9:
        best_value = model.objVal
        output(X, Y, W)
        print('cost_suite: ', cost_suite.getValue())
        print('cost_room: ', cost_room.getValue())
        print('cost_3: ', cost_3.getValue())
        print('cost_4: ', cost_4.getValue())
        print('objective: ', best_value, '\ntime: ', t_e - t_s)
        # 输出lp文件
        model.write('model.lp')
    else:
        print('未求出可行解')
        model.write('model.lp')

