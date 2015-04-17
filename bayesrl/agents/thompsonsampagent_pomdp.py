from modelbasedagent import ModelBasedAgent
import numpy as np

class ThompsonSampAgentPOMDP(ModelBasedAgent):
    def __init__(self, observation_model, dirichlet_param, reward_param, **kwargs):
        super(ThompsonSampAgentPOMDP, self).__init__(**kwargs)
        self.dirichlet_param = dirichlet_param
        self.reward_param = reward_param

        self.reward = np.full((self.num_states, self.num_actions, self.num_states), self.reward_param)
        self.belief = np.array([1./self.num_states for _ in range(self.num_states)])
        self.observation_model = observation_model
        self.__compute_policy()

    def reset(self):
        super(ThompsonSampAgentPOMDP, self).reset()
        self.reward.fill(self.reward_param)
        self.belief.fill(1./self.num_states)
        self.__compute_policy()

    def interact(self, reward, observation, next_state_is_terminal, idx):
        # Handle start of episode.
        if reward is None:
            # Return random action since there is no information.
            next_action = np.random.randint(self.num_actions)
            self.last_action = next_action
            self.belief = self.__observe(observation, self.belief)
            return self.last_action

        # Handle completion of episode.
        if next_state_is_terminal:
            # Proceed as normal.
            pass

        for last_state,next_state in [(s,s_) for s in range(self.num_states) for s_ in range(self.num_states)]:
            tp = self.belief[last_state]*self.transition_probs[last_state,self.last_action,next_state]
            # Update the reward associated with (s,a,s') if first time.
            #if self.reward[last_state, self.last_action, next_state] == self.reward_param:
            self.reward[last_state, self.last_action, next_state] *= (1-tp)
            self.reward[last_state, self.last_action, next_state] += reward*tp

            # Update set of states reached by playing a.
            self.transition_observations[last_state, self.last_action, next_state] += tp

        # Update transition probabilities after every T steps
        if self.policy_step == self.T:
            self.__compute_policy()

        self.belief = self.__new_belief(self.last_action,observation)
        # Choose next action according to policy.
        value_table = sum(self.belief[s]*self.value_table[s] for s in range(self.num_states))
        next_action = self._argmax_breaking_ties_randomly(value_table)

        self.policy_step += 1
        self.last_action = next_action

        return self.last_action

    def __compute_policy(self):
        """Compute an optimal T-step policy for the current state."""
        self.policy_step = 0
        transition_probs = np.zeros((self.num_states, self.num_actions, self.num_states))
        for s in xrange(self.num_states):
            for a in xrange(self.num_actions):
                transition_probs[s,a] = np.random.dirichlet(self.transition_observations[s,a] +\
                                                            self.dirichlet_param, size=1)
        self._value_iteration(transition_probs)
        self.transition_probs = transition_probs

    def __new_belief(self, action, observation):
        # Assumes: first does the action, then gets the observation
        #
        belief = self.__transition(action)
        return self.__observe(observation, belief)

    def __transition(self, action):
        belief = [0]*self.num_states
        for s in range(self.num_states):
            belief[s] = sum(self.transition_probs[s_,action,s]*self.belief[s_] for s_ in range(self.num_states))
        return np.array(belief)

    def __observe(self, observation, belief):
        belief = [belief[s]*self.observation_model[s][observation] for s in range(self.num_states)]
        Z = sum(belief)
        belief = np.array(belief)/float(Z)
        return belief