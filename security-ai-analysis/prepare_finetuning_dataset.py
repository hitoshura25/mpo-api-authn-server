#!/usr/bin/env python3
"""
Prepare Fine-Tuning Dataset for OLMo Security Remediation
Formats the narrativized data for OLMo fine-tuning
"""
import json
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from datasets import Dataset, DatasetDict


class FineTuningDatasetPreparer:
    """Prepare dataset specifically for OLMo fine-tuning"""
    
    def __init__(self, narratives_dir: str = "data/narrativized_security"):
        self.narratives_dir = Path(narratives_dir)
        self.training_examples = []
        self.validation_examples = []
        
    def load_training_pairs(self) -> List[Dict]:
        """Load the training pairs from narrativized data"""
        pairs = []
        
        # Find the most recent training pairs file
        training_files = list(self.narratives_dir.glob("training_pairs_*.jsonl"))
        if not training_files:
            print("❌ No training pairs found. Run create_narrativized_dataset.py first")
            return []
        
        latest_file = max(training_files, key=lambda x: x.stat().st_mtime)
        print(f"📖 Loading training pairs from: {latest_file.name}")
        
        with open(latest_file, 'r') as f:
            for line in f:
                pairs.append(json.loads(line))
        
        return pairs
    
    def load_security_journal(self) -> str:
        """Load the security journal for continuous training"""
        journal_files = list(self.narratives_dir.glob("security_journal_*.txt"))
        if not journal_files:
            return ""
        
        latest_journal = max(journal_files, key=lambda x: x.stat().st_mtime)
        print(f"📖 Loading security journal from: {latest_journal.name}")
        
        with open(latest_journal, 'r') as f:
            return f.read()
    
    def format_for_instruction_tuning(self, pair: Dict) -> str:
        """Format a training pair for instruction fine-tuning"""
        # OLMo responds well to clear structure
        formatted = f"""### Instruction:
{pair['instruction']}

### Input:
{pair['input']}

### Response:
{pair['output']}"""
        return formatted
    
    def format_for_continuous_training(self, journal_text: str) -> List[str]:
        """Split journal into chunks for continuous training"""
        # Split by narrative sections
        narratives = journal_text.split("="*80)
        
        # Clean and filter narratives
        cleaned = []
        for narrative in narratives:
            narrative = narrative.strip()
            if len(narrative) > 100:  # Filter out empty or very short sections
                cleaned.append(narrative)
        
        return cleaned
    
    def add_webauthn_specific_examples(self):
        """Add WebAuthn-specific security examples"""
        webauthn_examples = [
            {
                "instruction": "Fix the missing credential validation in WebAuthn implementation",
                "input": "The credential.response is not being validated properly",
                "output": """Add comprehensive credential validation:

```javascript
async function validateWebAuthnCredential(credential) {
    // 1. Validate credential structure
    if (!credential || !credential.response) {
        throw new Error('Invalid credential structure');
    }
    
    // 2. Validate client data
    const clientDataJSON = credential.response.clientDataJSON;
    const clientData = JSON.parse(
        new TextDecoder().decode(clientDataJSON)
    );
    
    // 3. Verify challenge
    if (clientData.challenge !== expectedChallenge) {
        throw new Error('Challenge verification failed');
    }
    
    // 4. Verify origin
    if (clientData.origin !== window.location.origin) {
        throw new Error('Origin verification failed');
    }
    
    // 5. Verify type
    if (clientData.type !== 'webauthn.create' && 
        clientData.type !== 'webauthn.get') {
        throw new Error('Invalid credential type');
    }
    
    return true;
}
```

This validation ensures the credential is legitimate and prevents bypass attacks."""
            },
            {
                "instruction": "Secure the WebAuthn session management",
                "input": "Sessions are not properly secured after WebAuthn authentication",
                "output": """Implement secure session configuration:

```javascript
const sessionConfig = {
    name: 'webauthn_session',
    secret: process.env.SESSION_SECRET, // Strong random secret
    resave: false,
    saveUninitialized: false,
    rolling: true, // Refresh session on activity
    cookie: {
        secure: true, // HTTPS only
        httpOnly: true, // No JavaScript access
        sameSite: 'strict', // CSRF protection
        maxAge: 1000 * 60 * 15, // 15 minutes
        path: '/',
        domain: process.env.COOKIE_DOMAIN
    },
    store: new RedisStore({ // Use Redis for production
        client: redisClient,
        prefix: 'webauthn:sess:',
        ttl: 900 // 15 minutes
    })
};

app.use(session(sessionConfig));

// Add session validation middleware
app.use((req, res, next) => {
    if (req.session && req.session.userId) {
        // Validate session is still valid
        validateSession(req.session)
            .then(() => next())
            .catch(() => {
                req.session.destroy();
                res.status(401).json({ error: 'Session expired' });
            });
    } else {
        next();
    }
});
```

This configuration ensures sessions are secure and protected against common attacks."""
            },
            {
                "instruction": "Fix GitHub Actions workflow permissions",
                "input": "Workflow has excessive permissions with write-all",
                "output": """Replace broad permissions with minimal required permissions:

```yaml
# Before (INSECURE):
name: Deploy
permissions: write-all

# After (SECURE):
name: Deploy
permissions:
  contents: read        # Read repository content
  packages: write       # Only if publishing packages
  deployments: write    # Only if creating deployments
  
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read    # Job-specific minimal permissions
      id-token: write   # For OIDC authentication
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        run: ./deploy.sh
```

Apply principle of least privilege - grant only necessary permissions."""
            }
        ]
        
        self.training_examples.extend(webauthn_examples)
    
    def create_fine_tuning_dataset(self):
        """Create the complete fine-tuning dataset"""
        
        # Load training pairs
        pairs = self.load_training_pairs()
        print(f"📊 Loaded {len(pairs)} training pairs")
        
        # Load security journal
        journal = self.load_security_journal()
        journal_chunks = self.format_for_continuous_training(journal)
        print(f"📊 Created {len(journal_chunks)} journal chunks")
        
        # Add WebAuthn-specific examples
        self.add_webauthn_specific_examples()
        print(f"📊 Added WebAuthn-specific examples")
        
        # Format all examples
        all_examples = []
        
        # Add instruction-tuned examples
        for pair in pairs:
            all_examples.append({
                "text": self.format_for_instruction_tuning(pair),
                "type": "instruction"
            })
        
        # Add journal narratives for context
        for chunk in journal_chunks[:20]:  # Limit for initial training
            all_examples.append({
                "text": chunk,
                "type": "narrative"
            })
        
        # Add WebAuthn examples
        for example in self.training_examples:
            all_examples.append({
                "text": self.format_for_instruction_tuning(example),
                "type": "webauthn_specific"
            })
        
        # Shuffle and split into train/validation
        random.shuffle(all_examples)
        split_point = int(len(all_examples) * 0.9)
        
        train_examples = all_examples[:split_point]
        val_examples = all_examples[split_point:]
        
        print(f"\n📊 Dataset Statistics:")
        print(f"  - Training examples: {len(train_examples)}")
        print(f"  - Validation examples: {len(val_examples)}")
        
        return train_examples, val_examples
    
    def save_for_huggingface(self, train_examples: List, val_examples: List):
        """Save dataset in Hugging Face format"""
        output_dir = Path("data/finetuning_dataset")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create Hugging Face dataset
        train_dataset = Dataset.from_list(train_examples)
        val_dataset = Dataset.from_list(val_examples)
        
        dataset_dict = DatasetDict({
            'train': train_dataset,
            'validation': val_dataset
        })
        
        # Save to disk
        dataset_path = output_dir / "olmo_security_dataset"
        dataset_dict.save_to_disk(str(dataset_path))
        print(f"✅ Hugging Face dataset saved to: {dataset_path}")
        
        # Also save as JSONL for other tools
        train_jsonl = output_dir / "train.jsonl"
        with open(train_jsonl, 'w') as f:
            for example in train_examples:
                f.write(json.dumps(example) + '\n')
        
        val_jsonl = output_dir / "validation.jsonl"
        with open(val_jsonl, 'w') as f:
            for example in val_examples:
                f.write(json.dumps(example) + '\n')
        
        print(f"✅ JSONL files saved to: {output_dir}")
        
        # Create training script
        self.create_training_script(output_dir)
        
        return dataset_path
    
    def create_training_script(self, output_dir: Path):
        """Create a ready-to-use training script"""
        script_content = '''#!/usr/bin/env python3
"""
Fine-tune OLMo on security remediation dataset
Run this on Google Colab or a machine with GPU
"""
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from datasets import load_from_disk
import torch

# Load dataset
dataset = load_from_disk("olmo_security_dataset")

# Load model and tokenizer
model_name = "allenai/OLMo-1B"
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    trust_remote_code=True,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
)
tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    trust_remote_code=True
)

# Set pad token
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# Tokenize dataset
def tokenize_function(examples):
    return tokenizer(
        examples["text"],
        truncation=True,
        padding="max_length",
        max_length=512
    )

tokenized_dataset = dataset.map(tokenize_function, batched=True)

# Training arguments
training_args = TrainingArguments(
    output_dir="./olmo-security-finetuned",
    overwrite_output_dir=True,
    num_train_epochs=3,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    warmup_steps=100,
    weight_decay=0.01,
    logging_dir="./logs",
    logging_steps=10,
    save_steps=500,
    eval_steps=500,
    evaluation_strategy="steps",
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    fp16=torch.cuda.is_available(),
    push_to_hub=False,  # Set to True to upload to Hugging Face
)

# Data collator
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False,
)

# Create trainer
trainer = Trainer(
    model=model,
    args=training_args,
    data_collator=data_collator,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["validation"],
)

# Train
print("Starting training...")
trainer.train()

# Save model
trainer.save_model("./olmo-security-finetuned")
tokenizer.save_pretrained("./olmo-security-finetuned")

print("✅ Training complete! Model saved to ./olmo-security-finetuned")
'''
        
        script_path = output_dir / "train_olmo.py"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Create Colab notebook
        colab_content = '''# OLMo Security Fine-Tuning Notebook

## Setup
```python
!pip install transformers datasets torch accelerate

# Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')

# Upload your dataset files to Drive first
!cp -r /content/drive/MyDrive/olmo_security_dataset .
```

## Training
```python
''' + script_content + '''
```

## Test the Fine-Tuned Model
```python
from transformers import pipeline

# Load fine-tuned model
generator = pipeline(
    "text-generation",
    model="./olmo-security-finetuned",
    device=0 if torch.cuda.is_available() else -1
)

# Test with a security issue
prompt = """### Instruction:
Fix the missing credential validation in WebAuthn implementation

### Input:
The credential.response is not being validated properly

### Response:"""

result = generator(prompt, max_new_tokens=200, temperature=0.3)
print(result[0]['generated_text'])
```
'''
        
        notebook_path = output_dir / "train_olmo_colab.md"
        with open(notebook_path, 'w') as f:
            f.write(colab_content)
        
        print(f"✅ Training script saved to: {script_path}")
        print(f"✅ Colab notebook saved to: {notebook_path}")


def main():
    print("🎯 Preparing Fine-Tuning Dataset for OLMo")
    print("="*60)
    
    preparer = FineTuningDatasetPreparer()
    
    # Create the dataset
    train_examples, val_examples = preparer.create_fine_tuning_dataset()
    
    # Save in multiple formats
    dataset_path = preparer.save_for_huggingface(train_examples, val_examples)
    
    print("\n✅ Dataset preparation complete!")
    print("\n🚀 Next steps:")
    print("1. Upload data/finetuning_dataset to Google Colab or GPU machine")
    print("2. Run: python train_olmo.py")
    print("3. Or use the Colab notebook: train_olmo_colab.md")
    print("\n📝 For Google Colab:")
    print("   - Upload the dataset folder to Google Drive")
    print("   - Open train_olmo_colab.md in Colab")
    print("   - Enable GPU runtime (Runtime -> Change runtime type -> GPU)")
    print("   - Run all cells")


if __name__ == "__main__":
    main()
