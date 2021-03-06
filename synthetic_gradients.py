# -*- coding: utf-8 -*-
"""synthetic_gradients.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1m_bvTUcAlCFP-1J6TlPNJFXHiHk7KqgC
"""

import numpy as np
import sys

def generate_dataset(output_dim = 8,num_examples=1000):
    def int2vec(x,dim=output_dim):
        out = np.zeros(dim)
        binrep = np.array(list(np.binary_repr(x))).astype('int')
        out[-len(binrep):] = binrep
        return out

    x_left_int = (np.random.rand(num_examples) * 2**(output_dim - 1)).astype('int')
    x_right_int = (np.random.rand(num_examples) * 2**(output_dim - 1)).astype('int')
    y_int = x_left_int + x_right_int

    x = list()
    for i in range(len(x_left_int)):
        x.append(np.concatenate((int2vec(x_left_int[i]),int2vec(x_right_int[i]))))

    y = list()
    for i in range(len(y_int)):
        y.append(int2vec(y_int[i]))

    x = np.array(x)
    y = np.array(y)
    
    return (x,y)

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def sigmoid_out2deriv(out):
    return out * (1 - out)

"""*forward_and_synthetic_update* is where the magic happens. We generate our synthetic gradient by passing our output through a non-linearity. This part could be a more complicated neural network, but from the experimental results of the paper we know that a simple linear layer works very well.

In *update_synthetic_gradients* we take the input to the synthetic gradient layer (self.output), and then perform an average outer product (matrix transpose -> matrix mul) with the output delta. It's like learning in a normal neural network, we've just got some special inputs and outputs.
"""

class DNI(object):
    
    def __init__(self,input_dim, output_dim,nonlin,nonlin_deriv,alpha = 0.1):
        
        self.weights = (np.random.randn(input_dim, output_dim) * 2) - 1
        self.bias = (np.random.randn(output_dim) * 2) - 1
        
        self.weights_0_1_synthetic_grads = (np.random.randn(output_dim,output_dim) * .0) - .0
        self.bias_0_1_synthetic_grads = (np.random.randn(output_dim) * .0) - .0
    
        self.nonlin = nonlin
        self.nonlin_deriv = nonlin_deriv
        self.alpha = alpha
    
    def forward_and_synthetic_update(self,input,update=True):
        # cache input
        self.input = input

        # forward propagate
        self.output = self.nonlin(self.input.dot(self.weights)  + self.bias)
        
        if(not update):
            return self.output
        else:
            # generate synthetic gradient via simple linear transformation
            self.synthetic_gradient = (self.output.dot(self.weights_0_1_synthetic_grads) + self.bias_0_1_synthetic_grads)

            # update our regular weights using synthetic gradient
            self.weight_synthetic_gradient = self.synthetic_gradient * self.nonlin_deriv(self.output)
            self.weights -= self.input.T.dot(self.weight_synthetic_gradient) * self.alpha
            self.bias -= np.average(self.weight_synthetic_gradient,axis=0) * self.alpha
        
       # return backpropagated synthetic gradient and forward propagated output 
        return self.weight_synthetic_gradient.dot(self.weights.T), self.output
    
    def normal_update(self,true_gradient):
        grad = true_gradient * self.nonlin_deriv(self.output)
        
        self.weights -= self.input.T.dot(grad) * self.alpha
        self.bias -= np.average(grad,axis=0) * self.alpha
        return grad.dot(self.weights.T)
    
    def update_synthetic_weights(self,true_gradient):
        self.synthetic_gradient_delta = (self.synthetic_gradient - true_gradient)
        self.weights_0_1_synthetic_grads -= self.output.T.dot(self.synthetic_gradient_delta) * self.alpha
        self.bias_0_1_synthetic_grads -= np.average(self.synthetic_gradient_delta,axis=0) * self.alpha

np.random.seed(1)

num_examples = 100
output_dim = 8
iterations = 10000

x,y = generate_dataset(num_examples=num_examples, output_dim = output_dim)

batch_size = 10
alpha = 0.01

input_dim = len(x[0])
layer_1_dim = 64
layer_2_dim = 32
output_dim = len(y[0])

layer_1 = DNI(input_dim,layer_1_dim,sigmoid,sigmoid_out2deriv,alpha)
layer_2 = DNI(layer_1_dim,layer_2_dim,sigmoid,sigmoid_out2deriv,alpha)
layer_3 = DNI(layer_2_dim, output_dim,sigmoid, sigmoid_out2deriv,alpha)

for iter in range(iterations):
    error = 0
    synthetic_error = 0
    
    for batch_i in range(int(len(x) / batch_size)):
        batch_x = x[(batch_i * batch_size):(batch_i+1)*batch_size]
        batch_y = y[(batch_i * batch_size):(batch_i+1)*batch_size]  
        
        _, layer_1_out = layer_1.forward_and_synthetic_update(batch_x)
        layer_1_delta, layer_2_out = layer_2.forward_and_synthetic_update(layer_1_out)
        layer_3_out = layer_3.forward_and_synthetic_update(layer_2_out,False)

        layer_3_delta = layer_3_out - batch_y
        layer_2_delta = layer_3.normal_update(layer_3_delta)
        layer_2.update_synthetic_weights(layer_2_delta)
        layer_1.update_synthetic_weights(layer_1_delta)
        
        error += (np.sum(np.abs(layer_3_delta)))
        synthetic_error += (np.sum(np.abs(layer_2_delta - layer_2.synthetic_gradient)))
    
    sys.stdout.write("\rIter:" + str(iter) + " Loss:" + str(error) + " Synthetic Loss:" + str(synthetic_error))
    if(iter % 1000 == 999):
        print("")

