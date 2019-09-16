% Predicting the output of the SIFT registration plugin,
% based on three manually constructed images.
% Frank Vernaillen, Sep 2019.

% Coordinate system used by the "Linear stack alignment with SIFT" plugin:
% the origin is in the TOP LEFT corner of the image, with the y-axis
% pointing down.

% Image is 1280 wide, 960 pixels high
w = 1280;
h = 960;

% Image center, in pixels
cx = w / 2;
cy = h / 2;

% Parameters of the
a = pi / 6;   % clockwise rotation
dx = 50;
dy = 100;

% Slice 1 to 2 transform (image 2 was created by shifting image 1 down 100
% pixels, and 50 pixels to the right.
T_1_to_2 = [1 0 dx;
            0 1 dy;
            0 0  1];
inv(T_1_to_2)  % = what SIFT returns = actually the transform from 2 to 1 (but the SIFT plugin says "1 to 2")

% Slice 2 to 3 transform (image 3 was created by just rotating image 1 over
% 30 degrees clockwise around the image center). Hence the transform from 2 to 3 first undoes the
% translation, then rotates about the center of the image.
Tc = [1 0 -cx; 
      0 1 -cy; 
      0 0   1];
R = [ cos(a) -sin(a) 0;
      sin(a)  cos(a) 0;
        0      0     1];
T_2_to_3 = inv(Tc) * R * Tc * inv(T_1_to_2);
inv(T_2_to_3)    % = what SIFT returns = actually the transform from 3 to 2 (but the SIFT plugin says "2 to 3")

