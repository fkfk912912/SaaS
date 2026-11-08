# 阅读导航：submit 返回任务 ID，_execute 串行执行，get 查询任务快照。
# 任务进度保存在当前进程；异步任务接口不等于可跨服务重启恢复的持久任务队列。

"""进程内有界评测任务队列；单 worker 串行执行，避免基线并发覆盖。"""
import asyncio
import copy
import time
import uuid


class EvaluationJobs:
    def __init__(self, capacity=8, retained=50, timeout=1800):
        self.capacity, self.retained, self.timeout = capacity, retained, timeout
        self.jobs = {}
        self.tasks = set()
        self.lock = asyncio.Lock()

    def submit(self, runner):
        # 提交时立即建立任务并返回 ID；实际执行由异步任务完成，调用方随后轮询结果。
        if sum(j['status'] in ('queued', 'running') for j in self.jobs.values()) >= self.capacity:
            raise RuntimeError('评测队列已满，请稍后再试')
        for key in list(self.jobs):
            if len(self.jobs) < self.retained:
                break
            if self.jobs[key]['status'] not in ('queued', 'running'):
                del self.jobs[key]
        job = dict(job_id=uuid.uuid4().hex, status='queued', completed=0, total=0,
                   created_at=time.time(), result=None, error=None)
        self.jobs[job['job_id']] = job
        task = asyncio.create_task(self._execute(job, runner))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return self.get(job['job_id'])

    def get(self, job_id):
        return copy.deepcopy(self.jobs.get(job_id))

    async def _execute(self, job, runner):
        # 锁让评测任务串行进入执行区，避免并发写同一基线；等待和执行状态分别记录。
        try:
            async with self.lock:
                job['status'] = 'running'
                def progress(completed, total):
                    job.update(completed=completed, total=total)
                job['result'] = await asyncio.wait_for(runner(progress), self.timeout)
                job['status'] = 'completed'
        except asyncio.CancelledError:
            job.update(status='cancelled', error='服务关闭，评测任务已取消')
            raise
        except asyncio.TimeoutError:
            job.update(status='failed', error='评测超过任务时间上限')
        except Exception as ex:
            job.update(status='failed', error=f'评测执行失败：{type(ex).__name__}')
        finally:
            job['finished_at'] = time.time()

    async def close(self):
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
