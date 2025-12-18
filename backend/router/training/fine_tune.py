"""
Fine-tuning manager for the intelligent router model.
Handles training, monitoring, and deployment of fine-tuned models.
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import os

import openai
from openai import OpenAI

from .dataset import generate_training_dataset, save_training_data
from ..config import ROUTER_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class FineTuneJob:
    """Represents a fine-tuning job."""
    job_id: str
    status: str
    model: str
    created_at: datetime
    training_file: str
    hyperparameters: Dict[str, Any]
    estimated_finish: Optional[datetime] = None
    fine_tuned_model: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


@dataclass
class FineTuneConfig:
    """Configuration for fine-tuning."""
    base_model: str = "gpt-4o-mini"
    n_epochs: int = 3
    batch_size: int = 16
    learning_rate_multiplier: float = 2.0
    suffix: Optional[str] = None
    validation_split: float = 0.1


class RouterFineTuner:
    """
    Manages fine-tuning of the intelligent router model.
    Handles dataset preparation, job monitoring, and model deployment.
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        self.client = OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
        self.active_jobs: Dict[str, FineTuneJob] = {}
        self.completed_jobs: List[FineTuneJob] = []

    def prepare_training_data(
        self,
        output_file: str = "router_training_data.jsonl",
        include_augmentation: bool = True,
        shuffle: bool = True
    ) -> str:
        """
        Prepare and save training data for fine-tuning.

        Args:
            output_file: Output filename for the training data
            include_augmentation: Whether to include augmented examples
            shuffle: Whether to shuffle the dataset

        Returns:
            Path to the saved training file
        """
        logger.info("Generating training dataset...")

        # Generate the dataset
        dataset = generate_training_dataset(
            include_augmentation=include_augmentation,
            shuffle=shuffle
        )

        # Save to file
        filepath = save_training_data(output_file)

        logger.info(f"Prepared {len(dataset)} training examples")
        return filepath

    def upload_training_file(self, filepath: str) -> str:
        """
        Upload training file to OpenAI.

        Args:
            filepath: Path to the training data file

        Returns:
            File ID from OpenAI
        """
        logger.info(f"Uploading training file: {filepath}")

        with open(filepath, "rb") as f:
            response = self.client.files.create(
                file=f,
                purpose="fine-tune"
            )

        file_id = response.id
        logger.info(f"Uploaded training file with ID: {file_id}")
        return file_id

    def start_fine_tuning(
        self,
        training_file_id: str,
        config: Optional[FineTuneConfig] = None
    ) -> FineTuneJob:
        """
        Start a fine-tuning job.

        Args:
            training_file_id: OpenAI file ID for training data
            config: Fine-tuning configuration

        Returns:
            FineTuneJob object representing the job
        """
        config = config or FineTuneConfig()

        # Set suffix if not provided
        if not config.suffix:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            config.suffix = f"syntra_router_{timestamp}"

        logger.info(f"Starting fine-tuning with model: {config.base_model}")

        # Start the fine-tuning job
        response = self.client.fine_tuning.jobs.create(
            training_file=training_file_id,
            model=config.base_model,
            hyperparameters={
                "n_epochs": config.n_epochs,
                "batch_size": config.batch_size,
                "learning_rate_multiplier": config.learning_rate_multiplier
            },
            suffix=config.suffix,
            validation_file=None  # Could add validation file later
        )

        # Create job object
        job = FineTuneJob(
            job_id=response.id,
            status=response.status,
            model=config.base_model,
            created_at=datetime.now(),
            training_file=training_file_id,
            hyperparameters={
                "n_epochs": config.n_epochs,
                "batch_size": config.batch_size,
                "learning_rate_multiplier": config.learning_rate_multiplier
            },
            estimated_finish=None  # Will be updated when job starts
        )

        self.active_jobs[response.id] = job
        logger.info(f"Started fine-tuning job: {response.id}")
        return job

    def check_job_status(self, job_id: str) -> FineTuneJob:
        """
        Check the status of a fine-tuning job.

        Args:
            job_id: Fine-tuning job ID

        Returns:
            Updated FineTuneJob object
        """
        try:
            response = self.client.fine_tuning.jobs.retrieve(job_id)

            # Update job object
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                job.status = response.status

                if hasattr(response, 'fine_tuned_model') and response.fine_tuned_model:
                    job.fine_tuned_model = response.fine_tuned_model

                if hasattr(response, 'trained_tokens') and response.trained_tokens:
                    job.metrics = {
                        "trained_tokens": response.trained_tokens,
                        "estimated_finish": getattr(response, 'estimated_finish', None)
                    }

                # Move to completed if finished
                if response.status in ['succeeded', 'failed', 'cancelled']:
                    self.completed_jobs.append(job)
                    del self.active_jobs[job_id]
                    logger.info(f"Job {job_id} completed with status: {response.status}")

                return job
            else:
                # Job not in active jobs, might be completed
                job = FineTuneJob(
                    job_id=response.id,
                    status=response.status,
                    model=getattr(response, 'model', 'unknown'),
                    created_at=datetime.now(),  # Approximate
                    training_file=getattr(response, 'training_file', 'unknown'),
                    hyperparameters={},
                    fine_tuned_model=getattr(response, 'fine_tuned_model', None)
                )
                return job

        except Exception as e:
            logger.error(f"Error checking job status for {job_id}: {e}")
            raise

    def list_jobs(self, status_filter: Optional[str] = None) -> List[FineTuneJob]:
        """
        List fine-tuning jobs.

        Args:
            status_filter: Filter by status (pending, running, succeeded, failed, cancelled)

        Returns:
            List of FineTuneJob objects
        """
        try:
            response = self.client.fine_tuning.jobs.list()

            jobs = []
            for job_data in response.data:
                if status_filter and job_data.status != status_filter:
                    continue

                job = FineTuneJob(
                    job_id=job_data.id,
                    status=job_data.status,
                    model=job_data.model,
                    created_at=datetime.fromtimestamp(job_data.created_at),
                    training_file=job_data.training_file,
                    hyperparameters=getattr(job_data, 'hyperparameters', {}),
                    fine_tuned_model=getattr(job_data, 'fine_tuned_model', None)
                )
                jobs.append(job)

            return jobs

        except Exception as e:
            logger.error(f"Error listing jobs: {e}")
            return []

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a fine-tuning job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancelled successfully
        """
        try:
            self.client.fine_tuning.jobs.cancel(job_id)

            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                job.status = "cancelled"
                self.completed_jobs.append(job)
                del self.active_jobs[job_id]

            logger.info(f"Cancelled fine-tuning job: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False

    def deploy_model(self, job_id: str) -> Optional[str]:
        """
        Deploy a completed fine-tuned model.

        Args:
            job_id: Job ID of the completed fine-tuning

        Returns:
            Fine-tuned model ID if deployment successful
        """
        job = self.check_job_status(job_id)

        if job.status != 'succeeded':
            logger.error(f"Cannot deploy job {job_id}: status is {job.status}")
            return None

        if not job.fine_tuned_model:
            logger.error(f"Job {job_id} succeeded but no fine-tuned model available")
            return None

        # Update the router config
        ROUTER_CONFIG.fine_tuned_model_id = job.fine_tuned_model
        ROUTER_CONFIG.use_fine_tuned = True

        logger.info(f"Deployed fine-tuned model: {job.fine_tuned_model}")
        return job.fine_tuned_model

    def get_job_metrics(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed metrics for a completed job.

        Args:
            job_id: Job ID

        Returns:
            Metrics dictionary or None
        """
        try:
            # Get job details
            job = self.check_job_status(job_id)

            if job.status != 'succeeded':
                return None

            # Try to get events (if available)
            events_response = self.client.fine_tuning.jobs.list_events(job_id)

            metrics = {
                "job_id": job_id,
                "status": job.status,
                "model": job.model,
                "fine_tuned_model": job.fine_tuned_model,
                "created_at": job.created_at.isoformat(),
                "events": []
            }

            # Add events
            for event in events_response.data:
                metrics["events"].append({
                    "timestamp": datetime.fromtimestamp(event.created_at).isoformat(),
                    "level": event.level,
                    "message": event.message
                })

            return metrics

        except Exception as e:
            logger.error(f"Error getting metrics for job {job_id}: {e}")
            return None

    def create_evaluation_dataset(
        self,
        test_size: int = 100,
        output_file: str = "router_eval_data.jsonl"
    ) -> str:
        """
        Create a separate evaluation dataset.

        Args:
            test_size: Number of examples for evaluation
            output_file: Output filename

        Returns:
            Path to evaluation file
        """
        logger.info(f"Creating evaluation dataset with {test_size} examples...")

        # Generate dataset without augmentation for cleaner evaluation
        dataset = generate_training_dataset(
            include_augmentation=False,
            shuffle=True
        )

        # Take a subset for evaluation
        eval_dataset = dataset[:test_size]

        # Save to file
        with open(output_file, 'w') as f:
            for item in eval_dataset:
                f.write(json.dumps(item) + '\n')

        logger.info(f"Saved evaluation dataset to {output_file}")
        return output_file

    def quick_train_and_deploy(
        self,
        config: Optional[FineTuneConfig] = None
    ) -> Optional[str]:
        """
        Quick workflow: prepare data, upload, train, and deploy.

        Args:
            config: Fine-tuning configuration

        Returns:
            Fine-tuned model ID if successful
        """
        try:
            # Step 1: Prepare training data
            training_file = self.prepare_training_data()

            # Step 2: Upload file
            file_id = self.upload_training_file(training_file)

            # Step 3: Start fine-tuning
            job = self.start_fine_tuning(file_id, config)

            logger.info(f"Training started. Job ID: {job.job_id}")
            logger.info("Monitor progress with: router_tuner.check_job_status(job_id)")
            logger.info("Deploy when complete with: router_tuner.deploy_model(job_id)")

            return job.job_id

        except Exception as e:
            logger.error(f"Error in quick training workflow: {e}")
            return None


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def estimate_training_cost(
    n_examples: int,
    base_model: str = "gpt-4o-mini",
    n_epochs: int = 3
) -> Dict[str, Any]:
    """
    Estimate the cost of fine-tuning.

    Args:
        n_examples: Number of training examples
        base_model: Base model for fine-tuning
        n_epochs: Number of epochs

    Returns:
        Cost estimation dictionary
    """
    # Rough token estimation per example
    tokens_per_example = 800  # System prompt + user + assistant

    total_tokens = n_examples * tokens_per_example * n_epochs

    # Cost per 1K tokens (rough estimates)
    costs = {
        "gpt-4o-mini": 0.003,  # $0.003 per 1K tokens for training
        "gpt-3.5-turbo": 0.008,
        "gpt-4": 0.03,
        "gpt-4o": 0.03
    }

    cost_per_1k = costs.get(base_model, 0.01)
    estimated_cost = (total_tokens / 1000) * cost_per_1k

    return {
        "estimated_tokens": total_tokens,
        "estimated_cost_usd": round(estimated_cost, 2),
        "cost_per_1k_tokens": cost_per_1k,
        "assumptions": "800 tokens per example, includes system prompt"
    }


def validate_training_file(filepath: str) -> Dict[str, Any]:
    """
    Validate a training file for fine-tuning.

    Args:
        filepath: Path to training file

    Returns:
        Validation results
    """
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()

        total_examples = len(lines)
        valid_examples = 0
        total_tokens = 0

        for line in lines:
            try:
                data = json.loads(line.strip())
                if validate_example_format(data):
                    valid_examples += 1
                    total_tokens += estimate_example_tokens(data)
            except json.JSONDecodeError:
                continue

        return {
            "total_examples": total_examples,
            "valid_examples": valid_examples,
            "invalid_examples": total_examples - valid_examples,
            "estimated_total_tokens": total_tokens,
            "is_valid": valid_examples > 0 and valid_examples == total_examples
        }

    except Exception as e:
        return {
            "error": str(e),
            "is_valid": False
        }


def validate_example_format(example: Dict[str, Any]) -> bool:
    """Validate that an example has the correct format."""
    required_keys = ["messages"]
    if not all(key in example for key in required_keys):
        return False

    messages = example.get("messages", [])
    if len(messages) != 3:  # system, user, assistant
        return False

    # Check message roles
    roles = [msg.get("role") for msg in messages]
    if roles != ["system", "user", "assistant"]:
        return False

    # Check content exists
    for msg in messages:
        if not msg.get("content"):
            return False

    return True


def estimate_example_tokens(example: Dict[str, Any]) -> int:
    """Roughly estimate tokens in an example."""
    total_chars = 0
    for msg in example.get("messages", []):
        total_chars += len(msg.get("content", ""))

    # Rough estimation: 4 chars per token
    return total_chars // 4


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

router_tuner = RouterFineTuner()
