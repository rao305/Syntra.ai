#!/usr/bin/env python3
"""
Train the Intelligent Router Model

This script handles the complete training pipeline for the Syntra AI router:
1. Prepare training data from examples
2. Upload to OpenAI for fine-tuning
3. Monitor training progress
4. Deploy the fine-tuned model

Usage:
    python scripts/train_router.py --help
"""

import argparse
import logging
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from router.training.fine_tune import router_tuner, FineTuneConfig, estimate_training_cost
from router.training.dataset import generate_training_dataset, save_training_data
from router import intelligent_router
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Train the Intelligent Router Model")
    parser.add_argument(
        "--mode",
        choices=["full", "prepare", "upload", "train", "monitor", "deploy"],
        default="full",
        help="Training mode (default: full pipeline)"
    )
    parser.add_argument(
        "--base-model",
        default="gpt-4o-mini",
        help="Base model for fine-tuning"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Training batch size"
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2.0,
        help="Learning rate multiplier"
    )
    parser.add_argument(
        "--suffix",
        help="Model suffix for identification"
    )
    parser.add_argument(
        "--output-file",
        default="router_training_data.jsonl",
        help="Output file for training data"
    )
    parser.add_argument(
        "--job-id",
        help="Job ID for monitoring/deploying existing job"
    )
    parser.add_argument(
        "--no-augmentation",
        action="store_true",
        help="Disable data augmentation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )

    args = parser.parse_args()

    try:
        if args.mode == "full":
            await run_full_pipeline(args)
        elif args.mode == "prepare":
            await prepare_data(args)
        elif args.mode == "upload":
            await upload_data(args)
        elif args.mode == "train":
            await start_training(args)
        elif args.mode == "monitor":
            await monitor_training(args)
        elif args.mode == "deploy":
            await deploy_model(args)

    except Exception as e:
        logger.error(f"Training failed: {e}")
        sys.exit(1)


async def run_full_pipeline(args):
    """Run the complete training pipeline."""
    logger.info("🚀 Starting full router training pipeline")

    if args.dry_run:
        logger.info("DRY RUN - Showing pipeline steps:")

        # Estimate cost
        cost_est = estimate_training_cost(
            n_examples=1000,
            base_model=args.base_model,
            n_epochs=args.epochs
        )
        logger.info(f"Estimated cost: ${cost_est['estimated_cost_usd']}")
        logger.info(f"Estimated tokens: {cost_est['estimated_tokens']:,}")

        logger.info("Pipeline steps:")
        logger.info("1. Prepare training data with augmentation")
        logger.info("2. Upload data to OpenAI")
        logger.info("3. Start fine-tuning job")
        logger.info("4. Monitor training progress")
        logger.info("5. Deploy fine-tuned model")
        return

    # Step 1: Prepare data
    logger.info("📚 Step 1: Preparing training data...")
    training_file = prepare_data_sync(args)

    # Step 2: Upload data
    logger.info("☁️  Step 2: Uploading training data...")
    file_id = router_tuner.upload_training_file(training_file)

    # Step 3: Start training
    logger.info("🎯 Step 3: Starting fine-tuning...")
    config = FineTuneConfig(
        base_model=args.base_model,
        n_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate_multiplier=args.learning_rate,
        suffix=args.suffix
    )

    job = router_tuner.start_fine_tuning(file_id, config)
    logger.info(f"✅ Training started! Job ID: {job.job_id}")

    # Step 4: Monitor training
    logger.info("👀 Step 4: Monitoring training progress...")
    await monitor_job_until_complete(job.job_id)

    # Step 5: Deploy model
    logger.info("🚀 Step 5: Deploying fine-tuned model...")
    model_id = router_tuner.deploy_model(job.job_id)

    if model_id:
        logger.info("🎉 SUCCESS! Router training pipeline completed!")
        logger.info(f"🔥 Fine-tuned model deployed: {model_id}")
        logger.info("💡 The intelligent router is now using the fine-tuned model")
    else:
        logger.error("❌ Failed to deploy model")
        sys.exit(1)


def prepare_data_sync(args):
    """Prepare training data (synchronous wrapper)."""
    return router_tuner.prepare_training_data(
        output_file=args.output_file,
        include_augmentation=not args.no_augmentation
    )


async def prepare_data(args):
    """Prepare training data only."""
    logger.info("📚 Preparing training data...")

    filepath = router_tuner.prepare_training_data(
        output_file=args.output_file,
        include_augmentation=not args.no_augmentation
    )

    logger.info(f"✅ Training data saved to: {filepath}")

    # Show some stats
    with open(filepath, 'r') as f:
        lines = f.readlines()

    logger.info(f"📊 Dataset stats: {len(lines)} examples")

    # Estimate cost
    cost_est = estimate_training_cost(
        n_examples=len(lines),
        base_model=args.base_model,
        n_epochs=args.epochs
    )
    logger.info(f"💰 Estimated training cost: ${cost_est['estimated_cost_usd']}")
    logger.info(f"🔢 Estimated tokens: {cost_est['estimated_tokens']:,}")


async def upload_data(args):
    """Upload training data only."""
    if not os.path.exists(args.output_file):
        logger.error(f"Training file not found: {args.output_file}")
        logger.info("Run with --mode prepare first")
        sys.exit(1)

    logger.info("☁️  Uploading training data...")
    file_id = router_tuner.upload_training_file(args.output_file)
    logger.info(f"✅ Uploaded! File ID: {file_id}")


async def start_training(args):
    """Start training job only."""
    if not args.job_id:
        logger.error("Need --job-id for training mode")
        logger.info("Upload data first with --mode upload")
        sys.exit(1)

    logger.info("🎯 Starting fine-tuning job...")

    config = FineTuneConfig(
        base_model=args.base_model,
        n_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate_multiplier=args.learning_rate,
        suffix=args.suffix
    )

    job = router_tuner.start_fine_tuning(args.job_id, config)
    logger.info(f"✅ Training started! Job ID: {job.job_id}")


async def monitor_training(args):
    """Monitor training progress."""
    if not args.job_id:
        logger.error("Need --job-id for monitoring")
        sys.exit(1)

    logger.info(f"👀 Monitoring job: {args.job_id}")
    await monitor_job_until_complete(args.job_id)


async def deploy_model(args):
    """Deploy fine-tuned model."""
    if not args.job_id:
        logger.error("Need --job-id for deployment")
        sys.exit(1)

    logger.info(f"🚀 Deploying model from job: {args.job_id}")
    model_id = router_tuner.deploy_model(args.job_id)

    if model_id:
        logger.info(f"✅ Model deployed: {model_id}")
        logger.info("🔄 Router updated to use fine-tuned model")
    else:
        logger.error("❌ Failed to deploy model")
        sys.exit(1)


async def monitor_job_until_complete(job_id: str):
    """Monitor a job until completion."""
    import time

    while True:
        job = router_tuner.check_job_status(job_id)

        status = job.status
        logger.info(f"📊 Job {job_id}: {status}")

        if status == "succeeded":
            logger.info("✅ Training completed successfully!")
            if job.fine_tuned_model:
                logger.info(f"🤖 Fine-tuned model: {job.fine_tuned_model}")
            break
        elif status in ["failed", "cancelled"]:
            logger.error(f"❌ Training {status}")
            if hasattr(job, 'error') and job.error:
                logger.error(f"Error: {job.error}")
            sys.exit(1)

        # Wait before checking again
        await asyncio.sleep(60)  # Check every minute


if __name__ == "__main__":
    asyncio.run(main())

