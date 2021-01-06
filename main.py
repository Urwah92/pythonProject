from pade.misc.utility import display_message, start_loop
from pade.core.agent import Agent
from pade.acl.aid import AID
from pade.acl.messages import ACLMessage
from pade.behaviours.protocols import FipaContractNetProtocol
from sys import argv
from pade.behaviours.protocols import FipaRequestProtocol
from pade.behaviours.protocols import TimedBehaviour
import mysql.connector
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="welcomeurwah",
    database="L1_agent_1"
)
mycursor = db.cursor()
#mycursor.execute("CREATE TABLE agents (name VARCHAR(50), battery_efficiency FLOAT, battery_loss FLOAT)")
#mycursor.execute("ALTER TABLE agents ADD COLUMN State_of_charge FLOAT")
#mycursor.execute("ALTER TABLE agents ADD COLUMN Connection VARCHAR(255)")
#mycursor.execute("DELETE FROM agents")


class CompContNet1(FipaContractNetProtocol):
    '''CompContNet1

       Initial FIPA-ContractNet Behaviour that sends CFP messages
       to other feeder agents asking for restoration proposals.
       This behaviour also analyzes the proposals and selects the
       one it judges to be the best.'''

    def __init__(self, agent, message):
        super(CompContNet1, self).__init__(agent=agent, message=message, is_initiator=True)
        self.cfp = message

    def handle_propose(self, message):
        """
        """
        super(CompContNet1, self).handle_propose(message)

        display_message(self.agent.aid.name, 'PROPOSE message received')

    def handle_all_proposes(self, proposes):
        """
        """

        super(CompContNet1, self).handle_all_proposes(proposes)
        best_proposer = None
        higher_power = 0.0
        other_proposers = list()
        display_message(self.agent.aid.name, 'Analyzing proposals...')
        print(self.message.content)

        i = 1

        # logic to select proposals by the higher available power.
        for message in proposes:
            content = message.content
            split_msg = content.split()
            power = float(split_msg[0])
            line_loss = float(split_msg[1])
            soc = float(split_msg[2])
            power = round(power - line_loss, ndigits=2)
            display_message(self.agent.aid.name, 'Analyzing proposal {i}'.format(i=i))
            display_message(self.agent.aid.name, 'Data Offered: {pot}'.format(pot=power))
            i += 1
            if power > higher_power and soc > 0.1:
                if best_proposer is not None:
                    other_proposers.append(best_proposer)

                higher_power = power
                best_proposer = message.sender
            else:
                other_proposers.append(message.sender)

        display_message(self.agent.aid.name, 'The best proposal was: {pot} '.format(pot=higher_power))

        if other_proposers != []:
            display_message(self.agent.aid.name, 'Sending REJECT_PROPOSAL...')
            answer = ACLMessage(ACLMessage.REJECT_PROPOSAL)
            answer.set_protocol(ACLMessage.FIPA_CONTRACT_NET_PROTOCOL)
            answer.set_content('')
            for agent in other_proposers:
                answer.add_receiver(agent)
                sql_formula = "UPDATE agents SET Selection= 'REJECTED' WHERE name= '" + str(agent.name) + "'"
                display_message(self.agent.aid.name, 'Updating Reject status of rejected agents...'.format(agent))
                mycursor.execute(sql_formula)
                db.commit()

            self.agent.send(answer)

        if best_proposer is not None:
            display_message(self.agent.aid.name, 'Sending ACCEPT_PROPOSAL...')
            display_message(self.agent.aid.name, 'Updating Accept Status... '.format(best_proposer))
            sql_formula = "UPDATE agents SET Selection= 'ACCEPTED' WHERE name= '" + str(best_proposer.name) + "'"
            mycursor.execute(sql_formula)
            db.commit()


class CompContNet2(FipaContractNetProtocol):
    '''CompContNet2

       FIPA-ContractNet Participant Behaviour that runs when an agent
       receives a CFP message. A proposal is sent and if it is selected,
       the restrictions are analized to enable the restoration.'''

    def __init__(self, agent):
        super(CompContNet2,self).__init__(agent=agent, message=None, is_initiator=False)

    def handle_cfp(self, message):
        """
        """
        self.agent.call_later(1.0, self._handle_cfp, message)

    def _handle_cfp(self, message):
        """
        """
        super(CompContNet2, self).handle_cfp(message)
        self.message = message

        display_message(self.agent.aid.name, 'CFP message received by: {}'.format(message.sender.name))
        mycursor.execute("SELECT name FROM agents WHERE name= '"+str(self.agent.aid.name)+"' AND Connection= '"+str(message.sender.name)+"'")
        agentdata_exist = mycursor.fetchone()
        # for exist in agentdata_exist:
        if agentdata_exist != None:
            split_msg = self.agent.pot_disp.split()
            sql_formula = "UPDATE agents SET battery_efficiency= " + split_msg[0] + ", battery_loss=" + split_msg[1] + " , State_of_charge = " + split_msg[2] + " WHERE name='"+str(message.sender.name)+"'"
            mycursor.execute(sql_formula)
            display_message(self.agent.aid.name, 'Updating agents Data...')


        else:
            split_msg = message.content.split()
            sql_formula = "INSERT INTO agents (name, battery_efficiency, battery_loss, State_of_charge) VALUES('"+str(message.sender.name)+"', " + split_msg[0] + ", " + split_msg[1] + ", " + split_msg[2] + ")"
            mycursor.execute(sql_formula)
            display_message(self.agent.aid.name, 'Inserting agents Data... {}')
        display_message(self.agent.aid.name, 'SOC Offered: {pot}'.format(pot=split_msg[2]))
        db.commit()

        answer = self.message.create_reply()
        answer.set_performative(ACLMessage.PROPOSE)
        answer.set_content(self.agent.pot_disp)
        self.agent.send(answer)

    def handle_accept_propose(self, message):
        display_message(self.agent.aid.name, ' ACCEPT_PROPOSAL Received By...{}'.format(message.sender.name))


    def handle_reject_propose(self, message):
        display_message(self.agent.aid.name, 'REJECT PROPOSAL RECEIVED By.....{}'.format(message.sender.name))


class CompContNet3(FipaContractNetProtocol):
    def __init__(self, agent):
        super(CompContNet3, self).__init__(agent=agent, message=None, is_initiator=False)

    def handle_cfp(self, message):
        """
        """
        self.agent.call_later(1.0, self._handle_cfp, message)

    def _handle_cfp(self, message):
        """
        """
        super(CompContNet3, self).handle_cfp(message)
        self.message = message

        display_message(self.agent.aid.name, 'CFP message received by Base Agent: {}'.format(message.content))

        answer = self.message.create_reply()
        answer.set_performative(ACLMessage.PROPOSE)

        sql_formula= "SELECT battery_efficiency, battery_loss, State_of_charge FROM agents WHERE Selection= 'ACCEPTED' AND Connection= '" +str(self.agent.aid.name)+ "'"
        mycursor.execute(sql_formula)
        result= mycursor.fetchall()# idhr say setting karni ha
        temp= str(result[0][0])+" "+str(result[0][1])+" "+ str(result[0][2])
        answer.set_content(temp)

        self.agent.send(answer)
        db.commit()

    def handle_accept_propose(self, message):
        display_message(self.agent.aid.name, ' ACCEPT_PROPOSAL Received...')
        sql_formula = "UPDATE agents SET Selection= 'ACCEPTED' WHERE Selection= 'ACCEPTED' AND Connection= '" + str(self.agent.aid.name) + "'"
        mycursor.execute(sql_formula)
        db.commit()
        message2 = ACLMessage(ACLMessage.REQUEST)
        message2.set_protocol(ACLMessage.FIPA_REQUEST_PROTOCOL)
        message2.set_content('SOC')
        sql_formula2= "SELECT name FROM agents WHERE Selection= 'ACCEPTED' AND Connection= '" + str(self.agent.aid.name) + "' "
        message2.add_receiver(AID(name=str(sql_formula2[0][0])))
        self.agent.send(message2)

    def handle_reject_propose(self, message):
        display_message(self.agent.aid.name, 'Reject Proposal Received.....')
        sql_formula2 = "UPDATE agents SET Selection = 'REJECTED2' WHERE Selection = 'ACCEPTED' AND Connection= '" + str(self.agent.aid.name) + "'"
        mycursor.execute(sql_formula2)
        db.commit()


'''******************************************************
'''


class CompRequest(FipaRequestProtocol):
    """FIPA Request Behaviour of the Time agent.: battery will receive request
    and give inform message to the upper layer agent"""
    def __init__(self, agent):
        super(CompRequest, self).__init__(agent=agent, message=None, is_initiator=False)

    def handle_request(self, message):
        super(CompRequest, self).handle_request(message)
        display_message(self.agent.aid.localname, 'Request message received: {}'.format(message.content))
        data = self.agent.pot_disp
        reply = message.create_reply()
        reply.set_performative(ACLMessage.INFORM)
        reply.set_content(data)
        self.agent.send(reply)


class CompRequest2(FipaRequestProtocol):
    """FIPA Request Behaviour of the Clock agent.: l1_agent_1 will keep on calling
    this class time after time to update the data by receiving inform message"""
    def __init__(self, agent, message):
        super(CompRequest2, self).__init__(agent=agent, message=message, is_initiator=True)

    def handle_inform(self, message):
        display_message(self.agent.aid.localname, "Sending Data by Inform Message...")
        msg_name=message.sender.name
        mycursor.execute("SELECT name FROM agents WHERE name='"+str(message.sender.name)+"'")
        agentdata_exist = mycursor.fetchone()

        if agentdata_exist != None:
            split_msg = message.content.split()
            sql_formula = "UPDATE agents SET battery_efficiency= " + split_msg[0] + ", battery_loss=" + split_msg[1] + " , State_of_charge = " + split_msg[2] + " WHERE name='"+str(message.sender.name)+"'"
            mycursor.execute(sql_formula)
            display_message(self.agent.aid.name, 'Updating agents Data...')

        else:
            split_msg = message.content.split()
            sql_formula = "INSERT INTO agents (name, battery_efficiency, battery_loss, State_of_charge) VALUES('"+str(message.sender.name)+"', " + split_msg[0] + ", " + split_msg[1] + ", " + split_msg[2] + ")"
            mycursor.execute(sql_formula)
            display_message(self.agent.aid.name, 'Entering New Data...')
        display_message(self.agent.aid.name, 'SOC Offered: {pot}'.format(pot=split_msg[2]))
        db.commit()

class ComportTemporal(TimedBehaviour):
    """Timed Behaviour of the Clock agent:"""
    def __init__(self, agent, time, message):
        super(ComportTemporal, self).__init__(agent, time)
        self.message = message

    def on_time(self):
        super(ComportTemporal, self).on_time()

        self.agent.send(self.message)


'''*************************************************************
'''

class L1Agent(Agent):

    def __init__(self, aid, participants):
        super(L1Agent, self).__init__(aid=aid, debug=False)

        message = ACLMessage(ACLMessage.CFP)
        message.set_protocol(ACLMessage.FIPA_CONTRACT_NET_PROTOCOL)
        message.set_content('SOC')

        message2 = ACLMessage(ACLMessage.REQUEST)
        message2.set_protocol(ACLMessage.FIPA_REQUEST_PROTOCOL)
        message2.set_content('Data')

        for participant in participants:
            message.add_receiver(AID(name=participant))
            message2.add_receiver(AID(name=participant))
            sql_formula = "UPDATE agents SET Connection= '" + str(self.aid.name) + "' WHERE name= '" + str(participant) + "'"
            mycursor.execute(sql_formula)

        self.call_later(8.0, self.launch_contract_net_protocol, message)
        self.call_later(12.0, self.launch_contract_net_protocol3)

        db.commit()

        self.comport_temp = ComportTemporal(self, 18.0, message2)
        self.comport_request = CompRequest2(self, message2)


        self.behaviours.append(self.comport_temp)
        self.behaviours.append(self.comport_request)


    def launch_contract_net_protocol(self, message):
        comp = CompContNet1(self, message)
        self.behaviours.append(comp)
        comp.on_start()
    def launch_contract_net_protocol3(self):
        comp = CompContNet3(self)
        self.behaviours.append(comp)


class AgentBattery(Agent):

    def __init__(self, aid, pot_disp):
        super(AgentBattery, self).__init__(aid=aid, debug=False)

        self.pot_disp = pot_disp

        comp = CompContNet2(self)
        self.comport_request = CompRequest(self)
        self.behaviours.append(self.comport_request)
        self.behaviours.append(comp)


class BaseAgent(Agent):
    def __init__(self, aid, participant):
        super(BaseAgent, self).__init__(aid=aid, debug=False)

        message = ACLMessage(ACLMessage.CFP)
        message.set_protocol(ACLMessage.FIPA_CONTRACT_NET_PROTOCOL)
        message.set_content('Test')

        for base_participants in participant:
            message.add_receiver(AID(name=base_participants))

        self.call_later(12.0, self.launch_contract_net_protocol, message)

    def launch_contract_net_protocol(self, message):
        comp = CompContNet1(self, message)
        self.behaviours.append(comp)
        comp.on_start()


if __name__ == "__main__":
    agents_per_process = 1
    c = 0
    agents = list()
    for i in range(agents_per_process):
        port = int(argv[1]) + c
        k = 100
        j = 200
        participants = list()
        participant = list()
        base_part = list()

        agent_name = 'agent_battery_{}@localhost:{}'.format(port - k, port - k)
        participants.append(agent_name)
        agente_part_1 = AgentBattery(AID(name=agent_name), '0.6 0.4 0.99')
        agents.append(agente_part_1)

        agent_name = 'agent_battery_{}@localhost:{}'.format(port + k, port + k)
        participants.append(agent_name)
        agente_part_4 = AgentBattery(AID(name=agent_name), '0.3 0.7 0.96')
        agents.append(agente_part_4)

        agent_name = 'L1agent_{}@localhost:{}'.format(port, port)
        base_part.append(agent_name)
        agente_init_5 = L1Agent(AID(name=agent_name), participants)
        agents.append(agente_init_5)

        agent_name = 'agent_battery_{}@localhost:{}'.format(port - j, port - j)
        participant.append(agent_name)
        agente_part_3 = AgentBattery(AID(name=agent_name), '0.4 0.3 0.95')
        agents.append(agente_part_3)

        agent_name = 'agent_battery_{}@localhost:{}'.format(port + j, port + j)
        participant.append(agent_name)
        agente_part_4 = AgentBattery(AID(name=agent_name), '0.7 0.6 0.98')
        agents.append(agente_part_4)

        agent_name = 'L1agent2_{}@localhost:{}'.format(port+50, port+50)
        base_part.append(agent_name)
        agente_init_6 = L1Agent(AID(name=agent_name), participant)
        agents.append(agente_init_6)

        agent_name = 'base_agent_{}@localhost:{}'.format(port+80, port+80)
        agente_init_7 = BaseAgent(AID(name= agent_name), base_part)
        agents.append(agente_init_7)

        c += 1000

    start_loop(agents)