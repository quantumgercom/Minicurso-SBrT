"""
Esse código já existe dentro da pasta do próprio simulador Netsquid.
Decidi coloca-lo aqui para motivos de estudos e realizei algumas alterações
de nomes para facilitar o entendimento
"""

from netsquid.components.qsource import QSource, SourceStatus
from netsquid.components.qprocessor import QuantumProcessor
from netsquid.qubits import ketstates as ks
from netsquid.qubits.state_sampler import StateSampler
from netsquid.components.models.delaymodels import FixedDelayModel
from netsquid.components.qchannel import QuantumChannel
from netsquid.nodes.network import Network

def example_network_setup(prep_delay=5, qchannel_delay=100, num_mem_positions=3):
    """Cria um exemplo de rede com o protocolo de emaranhamento de nós.

    Parameters
    ----------
    prep_delay : float, opcional
        Delay usado na fonte da rede. O padrão é 5 [ns].
    qchannel_delay : float, opcional
        Delay do canal quântico. O padrão é 100 [ns].
    num_mem_positions : int
        Número da posição das memoórias de ambos os nós na rede. Default is 3.

    Returns
    -------
    :class:`~netsquid.components.component.Component`
        Uma rede de componentes com nós e canais como subcomponentes.

    Notes
    -----
        Essa rede é também usado pelo matching integration test.

    """
    # Criando os nós:
    network = Network("Entangle_nodes")
    node_a, node_b = network.add_nodes(["node_A", "node_B"])
    # Criando os subcomponentes do nó 'a'
    node_a.add_subcomponent(QuantumProcessor(
        "QuantumMemoryATest", num_mem_positions, fallback_to_nonphysical=True))
    # Criando os subcomponentes do nó 'b'
    node_b.add_subcomponent(QuantumProcessor(
        "QuantumMemoryBTest", num_mem_positions, fallback_to_nonphysical=True))
    node_a.add_subcomponent(
        QSource("QSourceTest", state_sampler=StateSampler([ks.b00]),
                num_ports=2, status=SourceStatus.EXTERNAL,
                models={"emission_delay_model": FixedDelayModel(delay=prep_delay)}))
    # Criando um canal de comunicação quântico:
    qchannel = QuantumChannel("QuantumChannelTest", delay=qchannel_delay)
    # Criando as portas dos nós
    port_name_a, port_name_b = network.add_connection(
        node_a, node_b, channel_to=qchannel, label="quantum")
    # Alice terá a porta 'qout0' e 'qout1' e conectará a segunda com a 'qin0':
    node_a.subcomponents["QSourceTest"].ports["qout0"].forward_output(
        node_a.ports[port_name_a])
    node_a.subcomponents["QSourceTest"].ports["qout1"].connect(
        node_a.qmemory.ports["qin0"])
    # Bob terá uma conexão feita com a sua porta 'qin0' através da porta 'qout1' de Alice:
    node_b.ports[port_name_b].forward_input(node_b.qmemory.ports["qin0"])
    return network
