##this file is to update weight for automatically choosing the best route path
import torch
import torch.nn as nn

'''
class WeightPredictor(nn.Module):
    def __init__(self, input_size, num_cores):
        super(WeightPredictor, self).__init__()
        self.fc1 = nn.Linear(input_size + 1, 256)  # input_size + 1 for the action, change 64 to 256
        self.fc2 = nn.Linear(256, 256)  #change 64 to 256
        self.fc3_mesh = nn.Linear(256, 4)  # 4 weights for mesh_westfirst
        self.fc3_pt2pt = nn.Linear(256, num_cores * 3*(3*num_cores-1))  # num_cores*3 weights for Pt2Pt, too many parameter
        self.fc3_crossbar = nn.Linear(256, num_cores * 6)  # num_cores*6 weights for Pt2Pt

    def forward(self, state, action):
        # Ensure the action tensor has the same number of dimensions as state
        if action.dim() == 1:
            action = action.unsqueeze(1)  # Add a dimension to make it 2D
        
        x = torch.cat((state, action), dim=1)
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        
        # Output different weights based on action
        if action.item() == 0:  # Assuming 0 is mesh_westfirst
            weights = self.fc3_mesh(x)
        elif action.item() == 1 :  # Pt2Pt
            weights = self.fc3_pt2pt(x)
        else :  # crossbar
            weights = self.fc3_crossbar(x)
            
        # Apply ReLU to ensure weights are non-negative
        weights = torch.relu(weights)
        
        # Convert weights to integers by rounding, since in routingunit.cc and router.cc, they both are int not float
        weights = torch.round(weights).int()
        
        # Ensure all weights are non-zero by adding 1
        weights = weights + 1
        
        return weights
'''

class WeightPredictor(nn.Module):
    def __init__(self, input_size, num_cores):
        super(WeightPredictor, self).__init__()
        self.fc1 = nn.Linear(input_size + 1, 256)
        self.fc2 = nn.Linear(256, 256)
        self.dropout = nn.Dropout(p=0.5)  # Add dropout with 50% probability
        self.fc3_mesh = nn.Linear(256, 4)
        self.fc3_torus = nn.Linear(256, 4)
        self.fc3_fattree = nn.Linear(256, 2)
        self.fc3_flattenedbutterfly = nn.Linear(256, 2)  # Log2(num_cores)) k=4
        self.fc3_pt2pt = nn.Linear(256, num_cores * 3 * (3 * num_cores - 1)) #here num_cores=4
        self.fc3_crossbar = nn.Linear(256, num_cores * 6)#here num_cores=4

    def forward(self, state, action):
        if action.dim() == 1:
            action = action.unsqueeze(1)

        x = torch.cat((state, action), dim=1)
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)  # Apply dropout after the first layer
        x = torch.relu(self.fc2(x))

        if action.item() == 0:  # Assuming 0 is mesh_westfirst
            weights = self.fc3_mesh(x)
        elif action.item() == 1:  # Pt2Pt
            weights = self.fc3_pt2pt(x)
        elif  action.item() == 2:  # Crossbar
            weights = self.fc3_crossbar(x)
        elif  action.item() == 3:  # Torus
            weights = self.fc3_torus(x)
        elif  action.item() == 4:  # FatTree
            weights = self.fc3_fattree(x)
        else:  # FlattenedBufferfly
            weights = self.fc3_flattenedbutterfly(x)

        weights = torch.relu(weights)
        weights = torch.round(weights).int()
        weights = weights + 1
        
        weights = torch.clamp(weights, min=1, max=20)  # Clamp the weights between 1 and 15


        return weights

# Define the training loop
def train_model(model, train_loader, num_epochs=50, learning_rate=0.001):
    criterion = nn.MSELoss()  # Example loss function; adapt as needed
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)  # LR scheduler

    for epoch in range(num_epochs):
        model.train()  # Set the model to training mode

        for i, (states, actions, targets) in enumerate(train_loader):
            optimizer.zero_grad()

            # Forward pass
            outputs = model(states, actions)
            loss = criterion(outputs.float(), targets.float())

            # Backward pass and optimization
            loss.backward()
            optimizer.step()

        # Step the learning rate scheduler
        scheduler.step()

        if (epoch + 1) % 10 == 0:
            print(f'Epoch [{epoch + 1}/{num_epochs}], Loss: {loss.item():.4f}')

    print("Training complete.")
    return model