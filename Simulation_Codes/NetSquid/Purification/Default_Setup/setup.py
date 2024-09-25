"""
Este código já existe dentro do próprio simulador Netsquid.
Decidi fazer algumas alterações com a finalidade de facilitar o entendimento
do código e localizar para a nossa região
"""

import pydynaa as pd

from netsquid.components import ClassicalChannel, QuantumChannel
from netsquid.nodes.network import Network
from netsquid.components.qsource import QSource, SourceStatus
from netsquid.components.qprocessor import QuantumProcessor
from netsquid.qubits import ketstates as ks
from netsquid.qubits.state_sampler import StateSampler
from netsquid.components.models.delaymodels import FixedDelayModel, FibreDelayModel
from netsquid.components.models import DepolarNoiseModel
from netsquid.nodes.connections import DirectConnection
from netsquid.protocols.protocol import Signals
from netsquid.util.datacollector import DataCollector
from netsquid.qubits import qubitapi as qapi
from netsquid.examples.purify import (FilteringExample)

def example_network_setup(source_delay=1e5, source_fidelity_sq=0.8, depolar_rate=1000,
                          node_distance=20):
    """Criado um exemplo de rede para uso com o protocolo de purificação.

    Returns
    -------
    :class:`~netsquid.components.component.Component`
        Uma rede de componentes com nós e canais com subcomponentes.
        
    Notes
    -----
        Essa rede é também usada pelo matching integration test.

    """
    network = Network("purify_network")
    # Criando os dois nós que serão utilizados
    node_a, node_b = network.add_nodes(["node_A", "node_B"])
    node_a.add_subcomponent(QuantumProcessor(
        "QuantumMemory_A", num_positions=2, fallback_to_nonphysical=True,
        memory_noise_models=DepolarNoiseModel(depolar_rate)))
    state_sampler = StateSampler(
        [ks.b01, ks.s00],
        probabilities=[source_fidelity_sq, 1 - source_fidelity_sq])
    node_a.add_subcomponent(QSource(
        "QSource_A", state_sampler=state_sampler,
        models={"emission_delay_model": FixedDelayModel(delay=source_delay)},
        num_ports=2, status=SourceStatus.EXTERNAL))
    node_b.add_subcomponent(QuantumProcessor(
        "QuantumMemory_B", num_positions=2, fallback_to_nonphysical=True,
        memory_noise_models=DepolarNoiseModel(depolar_rate)))
    # Criando uma conexão direta entre os canais clássicos
    conn_cchannel = DirectConnection(
        "CChannelConn_AB",
        ClassicalChannel("CChannel_A->B", length=node_distance,
                         models={"delay_model": FibreDelayModel(c=200e3)}),
        ClassicalChannel("CChannel_B->A", length=node_distance,
                         models={"delay_model": FibreDelayModel(c=200e3)}))
    network.add_connection(node_a, node_b, connection=conn_cchannel)
    # node_A.connect_to(node_B, conn_cchannel)
    # Conectando os canais quânticos que serão utilizados
    qchannel = QuantumChannel("QChannel_A->B", length=node_distance,
                              models={"quantum_loss_model": None,
                                      "delay_model": FibreDelayModel(c=200e3)},
                              depolar_rate=0)
    port_name_a, port_name_b = network.add_connection(
        node_a, node_b, channel_to=qchannel, label="quantum")
    # As portas de Alice serão a 'qout1' e a 'qout0':
    node_a.subcomponents["QSource_A"].ports["qout1"].forward_output(
        node_a.ports[port_name_a])
    node_a.subcomponents["QSource_A"].ports["qout0"].connect(
        node_a.qmemory.ports["qin0"])
    # Bob possuirá apenas a porta 'qin0':
    node_b.ports[port_name_b].forward_input(node_b.qmemory.ports["qin0"])
    return network

def example_sim_setup(node_a, node_b, num_runs, epsilon=0.3):
    """Exemplo de criação de uma simulação para o protocolo de purificação

    Returns
    -------
    :class:`~netsquid.examples.purify.FilteringExample`
        Para rodar o protocolo de exemplo.
    :class:`pandas.DataFrame`
        Dataframe para a coleta de dados.

    """
    filt_example = FilteringExample(node_a, node_b, num_runs=num_runs, epsilon=0.3)

    def record_run(evexpr):
        # Devolvendo os dados de fidelidade de cada execução
        protocol = evexpr.triggered_events[-1].source
        result = protocol.get_signal_result(Signals.SUCCESS)
        # Lembrando da fidelidade
        q_A, = node_a.qmemory.pop(positions=[result["pos_A"]])
        q_B, = node_b.qmemory.pop(positions=[result["pos_B"]])
        f2 = qapi.fidelity([q_A, q_B], ks.b01, squared=True)
        return {"F2": f2, "pairs": result["pairs"], "time": result["time"]}

    # Coletando os dados de fidelidade de todo o processo
    dc = DataCollector(record_run, include_time_stamp=False,
                       include_entity_name=False)
    dc.collect_on(pd.EventExpression(source=filt_example,
                                     event_type=Signals.SUCCESS.value))
    return filt_example, dc
