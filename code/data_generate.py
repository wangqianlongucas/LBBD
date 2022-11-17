# -*- coding: utf-8 -*-
# @Time    : 2022/11/14 15:34
# @Author  : wangqianlong
# @email   ：17634233142@qq.com
# @FileName: data_generate.py

# we generate two sets of data, each with three hospitals, 20–160 patients,
# A one-week planning horizon, where there are five days per week.
# One dataset has three ORs per hospital (yielding easy SPs but a hard MP)
# The other has five ORs (yielding hard SPs but an easy MP).
# 6 – 10% of all patients identified as mandatory, set 10%

import pandas as pd
import random
from numpy import random as n_r

from parameters import *


def patients_generate(n_p, hs_t, n_d):
    # Total booked time, Health status score, Number of days elapsed from the referral date of patient p, Waiting cost
    # surgical times follows the truncated normal distribution with a mean of 160 minutes,
    # - a standard deviation of 40 minutes, and a lower bound of 45 and an upper bound of 480 minutes.
    # ρ_p Uniform distribution [1, 5], where 1 is least urgent 5 is the most urgent (Health status score)
    # α_p Uniform distribution [60, 120] days (Number of days elapsed)
    data = []
    title = ['id', 'TBT', 'HS', 'NDE', 'Type']  # type : mandatory - 0
    surgical_times = n_r.normal(loc=160, scale=40, size=(1, n_p)).tolist()[0]
    surgical_times = [int(s_t) for s_t in surgical_times]

    for p in range(n_p):
        tbt = surgical_times[p] if 45 <= surgical_times[p] <= 480 else 160
        hs = random.randint(1, 5)
        nde = random.randint(60, 120)
        type_p = 1 if hs * (n_d - nde) <= - hs_t else 2
        data.append([p, tbt, hs, nde, type_p])

    patients = pd.DataFrame(data, columns=title)
    return patients


def hospitals_generate(n_h, n_d):
    # Ghd Cost of opening the surgical suite in hospital h on day d Uniform distribution [1500, 2500]
    # Fhd Cost of opening an OR in hospital h on day d Uniform distribution [4000, 6000]
    # Bhd Regular operating hours of each OR on day d in hospital h
    # Uniform distribution [420, 480] minutes in 15-minutes intervals
    data = []
    title = ['Hos', 'd', 'Ghd', 'Fhd', 'Bhd']

    for Hos in range(n_h):
        for d in range(n_d):
            ghd = random.randint(1500, 2500)
            fhd = random.randint(4000, 6000)
            bhd = random.randint(0, 4) * 15 + 420
            data.append([Hos, d, ghd, fhd, bhd])

    hospitals = pd.DataFrame(data, columns=title)
    return hospitals


# random.seed(200)
# n_r.randint(200)
for instance_id in range(10, 20):
    num_patients = 20
    PA = patients_generate(num_patients, parameters['HS_threshold'], parameters['day'])
    # HOS = hospitals_generate(parameters['hospital'], parameters['day'])

    PA.to_csv(f'../data/patients_{num_patients}_{instance_id}.csv', index=False)
    # HOS.to_csv(f'../data/hospitals.csv', index=False)
