# LBBD
This repository is for  practice of Vahid(2017).

If you like it, remember to star it! Original paper citation:
Roshanaei V, Luong C, Aleman D M, et al. Propagating logic-based Benders’ decomposition approaches for distributed operating room scheduling[J]. European Journal of Operational Research, 2017, 257(2): 439-455.

The Logic-Based Benders Decomposition (LBBD) is an advanced decomposition technique used to solve large-scale combinatorial optimization problems by separating the problem into two parts: a master problem (MP) and several subproblems (SPs). This method generalizes the classical Benders Decomposition by allowing for optimization problems of any mathematical structure to be used in the SPs, not just linear ones.

In the LBBD approach:

1. **Master Problem (MP)**: This problem handles the primary decision variables and typically simplifies the full problem to a more tractable form. The MP provides a bound (either lower or upper, depending on the problem type) on the objective function of the full problem.

2. **Subproblems (SPs)**: Once the MP is solved to obtain values for the primary variables, these values are fixed, and the SPs utilize them to solve for the secondary decision variables. The SPs often contain the more complicated constraints of the original problem.

3. **Benders’ Cuts**: These are derived from the solutions of the SPs. If the solution of an SP indicates that the current solution of the MP is not feasible or not optimal, a Benders' cut is generated and added to the MP to exclude the current solution in subsequent iterations.

4. **Iterative Process**: The algorithm iterates between solving the MP with the added Benders' cuts and the SPs, refining the feasible region of the MP until convergence is achieved—either finding an optimal solution or determining that no feasible solution exists.

LBBD is particularly useful in situations where the SPs can leverage specific problem structures or where very strong SP-specific algorithms exist. It has been applied successfully to various problems including supply chain optimization, facility location, scheduling, and resource allocation.

**<u>For interpretation and sharing, see LBBD.pdf.</u>**
