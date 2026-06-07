# Research Interests

> This file defines research interests in a **three-tier structure**.
> Use it to score and classify papers. Follow the tier guide strictly.

---

## 🟢 Tier Guide

| Tier                | Score Range | Meaning                                                                               |
| ------------------- | :---------: | ------------------------------------------------------------------------------------- |
| **Core focus**      | 7.5 – 10.0  | Directly aligned. Novel, technically deep, clearly advances the field.                |
| **Also relevant**   |  5.0 – 7.4  | Related in topic or method, but not the primary focus or contribution is incremental. |
| **Not priority**    |  2.0 – 4.9  | Broadly in the field but too applied, too narrow, or not directly useful.             |
| **General / Other** |  0.0 – 1.9  | Does not fit any of the four directions below. Assign this direction name literally.  |

**Scoring precision**: Output scores as **decimals** (e.g., 7.4, 8.2, 5.6).
Do NOT round to integers or 0.5 increments. This is important for ranking.

**Direction assignment**: If a paper spans multiple directions, assign the one that best captures its primary contribution. Do not create new direction names — use exactly one of the four names below, or `General / Other`.

**Overlap rule**: Directions 1 and 2 can overlap. Prefer:

- Direction 1 if the paper's main contribution is an _information-theoretic result_
- Direction 2 if the paper's main contribution is a _physical/thermodynamic result_

---

## 1. Quantum Information

> Theory of what quantum information is, how it flows, and what limits it.
> Includes both purely mathematical results and physically-motivated proofs.

**🟢 Core focus**:

- Entanglement theory: detection, distillation, measures (entanglement entropy,
  negativity, squashed entanglement), monogamy inequalities
- Bell nonlocality and device-independent (DI) protocols: DI-QKD, DI-randomness
  certification, self-testing of states and measurements
- Quantum entropy and information measures: von Neumann entropy, min/max entropy,
  Rényi entropy, entropy accumulation theorem (EAT), smooth min-entropy
- Quantum cryptography security proofs (QKD security, composable security frameworks)

**🟡 Also relevant**:

- Quantum channel theory: channel capacities, quantum and private capacities,
  superadditivity, channel simulation
- Quantum error correction and fault tolerance: stabilizer codes, topological codes
  (toric code, surface code), threshold theorems, logical gates
- Quantum resource theories: magic (non-stabilizerness), coherence, asymmetry,
  athermality — especially operational characterizations
- Non-classical correlations beyond entanglement (quantum discord, coherence)
- Quantum steering and its applications to semi-DI protocols

**🔴 Not priority**:

- Quantum cellular automata and reversible quantum computation theory
- Quantum complexity theory (BQP, QMA, circuit complexity, T-count)
- Post-quantum cryptography (classical algorithms resistant to quantum attacks)
- Quantum machine learning without clear information-theoretic contribution
- Classical information theory or classical coding theory without quantum extension
- Topological insulators / topological phases without connection to quantum information

---

## 2. Information Thermodynamics

> Physics of classical, stochastic, or quantum systems with many degrees of freedom — equilibrium or not.
> Includes both theoretical and experimental papers.

**🟢 Core focus**:

- Non-equilibrium quantum thermodynamics: fluctuation theorems (Jarzynski, Crooks),
  work extraction, heat engines operating at the quantum scale
- Quantum thermodynamics viewed through an information-theoretic lens
  (e.g., work as information, quantum Landauer erasure, Maxwell's demon)
- Quantum speed limits and thermodynamic bounds on gate fidelity or protocol duration
- Thermodynamic efficiency of irreversible computing, reversible computing, or quantum computing
- Physical constraints on information processing: time duration, heat dissipation, work input, etc.

**🟡 Also relevant**:

- Quantum thermal machines: quantum Otto/Carnot engines, quantum refrigerators,
  quantum batteries — especially bounds on efficiency and power
- Thermalization and quantum chaos: eigenstate thermalization hypothesis (ETH),
  many-body localization (MBL), quantum chaos indicators (OTOCs, level statistics)
- Open quantum systems: Lindblad master equations, decoherence, quantum trajectories, non-Markovian dynamics
- Prethermalization: prethermal plateaus, Floquet heating, shadow of integrability

**🔴 Not priority**:

- Quantum phase transitions: quantum critical phenomena, quantum Ising model,
  conformal field theory, symmetry-protected topological (SPT) phases
- Tensor networks: DMRG, MPS, MERA, PEPS — applied to ground states, dynamics,
  or topological phases
- Floquet engineering and driven quantum systems (excluding trivial periodic driving)
- Dissipative phase transitions and quantum Zeno dynamics
- Quantum chaos and random matrix theory (RMT) in many-body context
- Entanglement dynamics in random circuits or chaotic systems
- Condensed matter focusing purely on electronic band structure or transport
  without quantum information/thermodynamics angle
- Quantum chemistry, DFT, or molecular dynamics simulations
- Experimental materials characterization (X-ray, neutron scattering) without
  clear connection to quantum information or thermodynamics

---

## 3. Quantum Networks

> Practical and theoretical aspects of transmitting quantum information between parties.

**🟢 Core focus**:

- Quantum repeaters: entanglement swapping, nested purification, memory-based
  repeater architectures, all-photonic repeaters
- Quantum memory for networking applications (rare-earth ions, atomic ensembles, NV)
- Multi-party quantum communication protocols (quantum secret sharing, conference key)
- Experimental demonstrations of quantum networks (even if small-scale or proof-of-concept)
- Quantum network architectures: routing, entanglement routing, multipartite
  entanglement distribution, network coding

**🟡 Also relevant**:

- Entanglement swapping, entanglement purification, and entanglement distillation
  in the network context
- Quantum key distribution (QKD): especially measurement-device-independent (MDI-QKD), twin-field (TF-QKD), continuous-variable (CV-QKD), device-independent (DI-QKD)
- Satellite-based quantum communication: free-space channels, atmospheric effects,
  global-scale entanglement distribution

**🔴 Not priority**:

- Classical optical communication or fiber technology (no quantum component)
- Specific QKD hardware engineering (laser stabilization, detector SNR) unless it
  involves a genuinely novel protocol or information-theoretic result
- Single-photon source engineering (quantum dots, defects) unless tied to
  a specific networking protocol or network architecture paper

---

## 4. Hybrid Quantum Systems

> Physical platforms for quantum information processing involving different quantum systems.
> Focus on characterization and application of such systems.

**🟢 Core focus**:

- Spin ensembles coupled to superconducting circuits: Tavis-Cummings model,
  superradiance and subradiance, inhomogeneous broadening, hole-burning
- Quantum transducers: microwave-to-optical conversion, spin-photon interfaces,
  piezoelectric transducers — for quantum networking with superconducting qubits
- Circuit QED: electromagnetic induced transparency, probe-pump scheme, Master equation

**🟡 Also relevant**:

- NV centres, SiV centres, and other colour-centre platforms (diamond, SiC)
- Trapped ions and neutral atoms (Rydberg arrays) for quantum computing
- Topological qubits and Majorana-based platforms (nanowire experiments)
- Silicon quantum dots and spin qubits (GaAs, Si/SiGe, 28Si)
- Electromechanical and optomechanical quantum systems coupled to qubits
- Superconducting qubits: transmon, fluxonium, heavy fluxonium — gate fidelity,
  coherence times, leakage, crosstalk, novel qubit designs

**🔴 Not priority**:

- Error correction at the hardware level: surface code experiments, magic state
  distillation, fault-tolerant gate demonstrations
- Photonic quantum computing: cluster state generation, Boson sampling,
  linear optical quantum computing (LOQC)
- Nano-fabrication process improvements without quantum performance benchmark
- Classical control electronics (DACs, FPGAs, cryogenic CMOS) unless demonstrating
  novel quantum control that improves qubit fidelity or coherence
- Materials science of superconductors (Tc, gap, vortices) without qubit context
- Quantum sensing and metrology (magnetometry, gravimetry) unless the platform
  directly advances qubit hardware or transduction
