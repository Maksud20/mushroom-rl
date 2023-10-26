from multiprocessing import Pipe
from multiprocessing import Process

from .vectorized_env import VectorizedEnvironment


def _parallel_env_worker(remote, env_class, use_generator, args, kwargs):

    if use_generator:
        env = env_class.generate(*args, **kwargs)
    else:
        env = env_class(*args, **kwargs)

    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                action = data[0]
                res = env.step(action)
                remote.send(res)
            elif cmd == 'reset':
                init_states = data[0]
                res = env.reset(init_states)
                remote.send(res)
            elif cmd in 'stop':
                env.stop()
            elif cmd == 'info':
                remote.send(env.info)
            elif cmd == 'seed':
                env.seed(int(data))
            else:
                raise NotImplementedError()
    finally:
        remote.close()


class ParallelEnvironment(VectorizedEnvironment):
    """
    Basic interface to run in parallel multiple copies of the same environment.
    This class assumes that the environments are homogeneus, i.e. have the same type and MDP info.

    """
    def __init__(self, env_class, *args, n_envs=-1, use_generator=False, **kwargs):
        """
        Constructor.

        Args:
            env_class (class): The environment class to be used;
            *args: the positional arguments to give to the constructor or to the generator of the class;
            n_envs (int, -1): number of parallel copies of environment to construct;
            use_generator (bool, False): wheather to use the generator to build the environment or not;
            **kwargs: keyword arguments to set to the constructor or to the generator;

        """
        assert n_envs > 1

        self._remotes, self._work_remotes = zip(*[Pipe() for _ in range(n_envs)])
        self._processes = [Process(target=_parallel_env_worker,
                                   args=(work_remote, env_class, use_generator, args, kwargs))
                           for work_remote in self._work_remotes]

        for p in self._processes:
            p.start()

        self._remotes[0].send(('info', None))
        mdp_info = self._remotes[0].recv()

        super().__init__(mdp_info, n_envs)

    def step_all(self, env_mask, action):
        for i, remote in enumerate(self._remotes):
            if env_mask[i]:
                remote.send(('step', action[i, :]))

        results = []
        for i, remote in enumerate(self._remotes):
            if env_mask[i]:
                results.extend(remote.recv())

        return zip(*results)  # FIXME!!!

    def reset_all(self, env_mask, state=None):
        for i in range(self._n_envs):
            state_i = state[i, :] if state is not None else None
            self._remotes[i].send(('reset', state_i))

        results = []
        for i, remote in enumerate(self._remotes):
            if env_mask[i]:
                results.extend(remote.recv())

        return zip(*results)  # FIXME!!!

    def seed(self, seed):
        for remote in self._remotes:
            remote.send(('seed', seed))

        for remote in self._remotes:
            remote.recv()

    def stop(self):
        for remote in self._remotes:
            remote.send(('stop', None))

    def __del__(self):
        for remote in self._remotes:
            remote.send(('close', None))
        for p in self._processes:
            p.join()

    @staticmethod
    def generate(env, *args, n_envs=-1, **kwargs):
        """
        Method to generate an array of multiple copies of the same environment, calling the generate method n_envs times

        Args:
            env (class): the environment to be constructed;
            *args: positional arguments to be passed to the constructor;
            n_envs (int, -1): number of environments to generate;
            **kwargs: keywords arguments to be passed to the constructor

        Returns:
            A list containing multiple copies of the environment.

        """
        use_generator = hasattr(env, 'generate')
        return ParallelEnvironment(env, *args, n_envs=n_envs, use_generator=use_generator, **kwargs)