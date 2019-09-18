function calculate_sift_correction(M, w, h)
    % M is a 2 x 3 matrix
    M(3,:) = [0 0 1];
    M
    
    old_center = [w/2 h/2 1]';
    
    % Current correction
    offset = old_center - M * old_center;
    offset(2) = -offset(2);  % flip y
    disp(offset)
    
    % Fixed correction
    offset = old_center - inv(M) * old_center;
    offset(2) = -offset(2);  % flip y
    disp(offset)
end
