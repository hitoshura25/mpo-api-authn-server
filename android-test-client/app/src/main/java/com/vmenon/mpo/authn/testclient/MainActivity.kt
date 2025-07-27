package com.vmenon.mpo.authn.testclient

import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.lifecycleScope
import com.vmenon.mpo.authn.testclient.databinding.ActivityMainBinding
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    private lateinit var viewModel: WebAuthnViewModel
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        viewModel = ViewModelProvider(this)[WebAuthnViewModel::class.java]
        
        setupUI()
        observeViewModel()
    }
    
    private fun setupUI() {
        binding.btnRegister.setOnClickListener {
            val username = binding.etUsername.text.toString().trim()
            val displayName = binding.etDisplayName.text.toString().trim()
            
            if (username.isEmpty() || displayName.isEmpty()) {
                showToast("Please enter both username and display name")
                return@setOnClickListener
            }
            
            registerUser(username, displayName)
        }
        
        binding.btnAuthenticate.setOnClickListener {
            val username = binding.etAuthUsername.text.toString().trim()
            
            if (username.isEmpty()) {
                showToast("Please enter username for authentication")
                return@setOnClickListener
            }
            
            authenticateUser(username)
        }
        
        binding.btnClearLogs.setOnClickListener {
            binding.tvLogs.text = ""
        }
    }
    
    private fun observeViewModel() {
        viewModel.isLoading.observe(this) { isLoading ->
            binding.progressBar.visibility = if (isLoading) View.VISIBLE else View.GONE
            binding.btnRegister.isEnabled = !isLoading
            binding.btnAuthenticate.isEnabled = !isLoading
        }
        
        viewModel.logMessages.observe(this) { messages ->
            binding.tvLogs.text = messages.joinToString("\n")
            // Scroll to bottom
            binding.scrollView.post {
                binding.scrollView.fullScroll(View.FOCUS_DOWN)
            }
        }
        
        viewModel.errorMessage.observe(this) { error ->
            error?.let {
                showToast("Error: $it")
                viewModel.clearError()
            }
        }
        
        viewModel.successMessage.observe(this) { success ->
            success?.let {
                showToast("Success: $it")
                viewModel.clearSuccess()
            }
        }
    }
    
    private fun registerUser(username: String, displayName: String) {
        lifecycleScope.launch {
            viewModel.registerUser(username, displayName, this@MainActivity)
        }
    }
    
    private fun authenticateUser(username: String) {
        lifecycleScope.launch {
            viewModel.authenticateUser(username, this@MainActivity)
        }
    }
    
    private fun showToast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }
}