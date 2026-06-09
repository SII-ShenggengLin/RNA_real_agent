# Agent Algorithm Papers Collection

Downloaded from NeurIPS 2024, ICML 2024, and ICLR 2025.

## Paper List

### 1. AGILE: A Novel Reinforcement Learning Framework of LLM Agents
- **File**: `01_AGILE_NeurIPS2024.pdf`
- **Conference**: NeurIPS 2024
- **arXiv**: 2405.14751
- **Abstract**: A novel reinforcement learning framework of LLM agents named AGILE (AGent that Interacts and Learns from Environments) designed to perform complex conversational tasks with users, leveraging LLMs, memory, tools, and interactions with experts. The agent possesses capabilities beyond conversation, including reflection, tool usage, and expert consultation. The LLM serves as the policy model, fine-tuned using labeled data of actions and the PPO algorithm.

### 2. Reinforcement Learning with Adaptive Regularization for Safe Control of Critical Systems
- **File**: `02_RLAR_NeurIPS2024.pdf`
- **Conference**: NeurIPS 2024
- **arXiv**: 2404.15199
- **Abstract**: RL with Adaptive Regularization (RL-AR), an algorithm that enables safe RL exploration by combining the RL policy with a policy regularizer that hard-codes the safety constraints. RL-AR performs policy combination via a "focus module," which determines the appropriate combination depending on the state.

### 3. JaxMARL: Multi-Agent RL Environments and Algorithms in JAX
- **File**: `03_JaxMARL_NeurIPS2024.pdf`
- **Conference**: NeurIPS 2024 (Datasets and Benchmarks Track)
- **arXiv**: 2311.10090
- **Abstract**: Benchmarks are crucial in the development of machine learning algorithms. JaxMARL provides multi-agent RL environments and algorithms implemented in JAX for GPU-accelerated training, significantly improving scalability.

### 4. Diffusion Actor-Critic with Entropy Regulator (DACER)
- **File**: `04_DACER_NeurIPS2024.pdf`
- **Conference**: NeurIPS 2024
- **arXiv**: 2405.15177
- **Abstract**: An online reinforcement learning algorithm that innovatively uses diffusion model reverse process as policy function for multi-modal action distributions. Addresses the limitation of traditional RL algorithms where policies are parameterized as diagonal Gaussian distributions.

### 5. Decision Mamba: A Multi-Grained State Space Model with Self-Evolution Regularization for Offline RL
- **File**: `05_DecisionMamba_NeurIPS2024.pdf`
- **Conference**: NeurIPS 2024
- **arXiv**: 2406.05427
- **Abstract**: Introduces a Mamba-based offline RL framework with coarse-grained state space model for long-range temporal dependencies and fine-grained state space model for return-to-go, state, and action interactions, plus self-evolution regularization for robustness against noisy demonstrations.

### 6. Mitigating Information Loss in Tree-Based Reinforcement Learning via Direct Optimization (SYMPOL)
- **File**: `06_SYMPOL_ICLR2025.pdf`
- **Conference**: ICLR 2025 (Spotlight, Top 5%)
- **arXiv**: 2408.08761
- **Abstract**: SYMPOL is a novel method for SYMbolic tree-based on-POLicy RL. Employs a tree-based model integrated with a policy gradient method, enabling the agent to learn and adapt its actions while maintaining interpretability. Enables gradient-based, end-to-end learning of interpretable, axis-aligned decision trees within standard on-policy RL algorithms.

### 7. eQMARL: Entangled Quantum Multi-Agent Reinforcement Learning for Distributed Cooperation over Quantum Channels
- **File**: `07_eQMARL_ICLR2025.pdf`
- **Conference**: ICLR 2025
- **arXiv**: 2405.17486
- **Abstract**: A distributed actor-critic framework that facilitates cooperation over a quantum channel and eliminates local observation sharing via a quantum entangled split critic. Agent policies are tuned through joint observation-value function estimation via joint quantum measurements.

### 8. LS-Imagine: Open-World Reinforcement Learning over Long Short-Term Imagination
- **File**: `08_LSImagine_ICLR2025.pdf`
- **Conference**: ICLR 2025 (Oral)
- **arXiv**: 2410.03618
- **Abstract**: Extends the imagination horizon within a limited number of state transition steps for visual RL agents in high-dimensional open worlds. Builds a long short-term world model with goal-conditioned jumpy state transitions and affordance maps for improved exploration in tasks like MineDojo.

### 9. TOP-ERL: Transformer-based Off-Policy Episodic Reinforcement Learning
- **File**: `09_TOPERL_ICLR2025.pdf`
- **Conference**: ICLR 2025
- **arXiv**: 2410.09536
- **Abstract**: Enables off-policy updates in the Episodic RL (ERL) framework where policies predict entire action trajectories over multiple time steps. Uses a Transformer-based critic that estimates values for segmented action sequences with N-step return estimation.

### 10. Efficient Adaptation in Mixed-Motive Environments via Hierarchical Opponent Modeling and Planning
- **File**: `10_EfficientAdaptation_ICML2024.pdf`
- **Conference**: ICML 2024
- **arXiv**: 2406.08002
- **Abstract**: Addresses efficiently adapting to co-players in mixed-motive environments through hierarchical opponent modeling and planning. Uses a hierarchical approach to model opponents and plan actions in multi-agent settings with mixed incentives.
