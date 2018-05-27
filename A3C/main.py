""" Asynchronous Advantage Actor-Critic Algorithm (A3C) for OpenAI Gym environment
"""

import sys
import gym
# import retro
import argparse
import threading
import numpy as np
import tensorflow as tf

from a3c import A3C
from tqdm import tqdm
from keras.backend.tensorflow_backend import set_session
from keras.utils import to_categorical
from keras import backend as K

episode = 0

def get_session():
    """ Limit session memory usage
    """
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    return tf.InteractiveSession(config=config)

def tfSummary(tag, val):
    """ Scalar Value Tensorflow Summary
    """
    return tf.Summary(value=[tf.Summary.Value(tag=tag, simple_value=val)])

def parse_args(args):
    """ Parse arguments from command line input
    """
    parser = argparse.ArgumentParser(description='Training parameters')
    #
    parser.add_argument('--n_threads', type=int, default=16, help="Number of threads")
    parser.add_argument('--nb_episodes', type=int, default=5000, help="Number of training episodes")
    parser.add_argument('--env', type=str, default='CartPole-v1',help="OpenAI Gym Environment")
    parser.add_argument('--gpu', type=int, default=0, help='GPU ID')
    parser.set_defaults(render=False)
    return parser.parse_args(args)

def training_thread(agent, nb_episodes, env, act_dim, summary_writer, isImage):
    """ Build threads to run shared computation across
    """
    global episode
    while episode < nb_episodes:

        # Reset episode
        time, cumul_reward, done = 0, 0, False
        old_state = env.reset()
        actions, states, rewards = [], [], []

        while not done:
            # Actor picks an action (following the policy)
            if(isImage): a = agent.policy_action(np.expand_dims(old_state, axis=0))
            else: a = agent.policy_action(old_state)
            # Retrieve new state, reward, and whether the state is terminal
            new_state, r, done, _ = env.step(a)
            # Memorize (s, a, r) for training
            actions.append(to_categorical(a, act_dim))
            rewards.append(r)
            states.append(old_state)
            # Update current state
            old_state = new_state
            cumul_reward += r
            time += 1

        # Train using discounted rewards ie. compute updates
        agent.train(states, actions, rewards, done)

        # Export results for Tensorboard
        score = tfSummary('score', cumul_reward)
        summary_writer.add_summary(score, global_step=episode)
        summary_writer.flush()
        episode += 1
        print("Episode ", episode, " score ", cumul_reward)

def main(args=None):

    # Parse arguments
    if args is None:
        args = sys.argv[1:]
    args = parse_args(args)

    # Check if a GPU ID was set
    if args.gpu:
        os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu
    set_session(get_session())
    summary_writer = tf.summary.FileWriter("./tensorboard_" + args.env)

    # Initialization
    dummy_env = gym.make(args.env)
    # dummy_env = retro.make(game='SonicTheHedgehog-Genesis', state='GreenHillZone.Act1', record='.')
    env_dim = dummy_env.observation_space.shape
    act_dim = dummy_env.action_space.n
    isImage = (len(env_dim)==3)
    a3c = A3C(act_dim, env_dim)

    # Create threads
    threads = [threading.Thread(target=training_thread, args=(a3c, args.nb_episodes, gym.make(args.env), act_dim, summary_writer, isImage)) for i in range(args.n_threads)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    # while True:
    #     dummy_env.render()
    #     a = a3c.policy_action(old_state)
    #     old_state, r, done, _ = env.step(a)
    #     time += 1
    #     if done: env.reset()


if __name__ == "__main__":
    main()
