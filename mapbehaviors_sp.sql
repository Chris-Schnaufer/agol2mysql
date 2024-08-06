drop function mapbehaviors;

DELIMITER //
create function mapbehaviors(b1 varchar(50),b2 varchar(50),b3 varchar(50),b4 varchar(50),b5 varchar(50))
returns varchar(1024) DETERMINISTIC
BEGIN
  declare result varchar(1024);
  set result = '';
  if b1 is not null then
    set result = b1;
  end if;
  if b2 is not null then
    set result = CONCAT(result, ',', b2);
  end if;
  if b3 is not null then
    set result = CONCAT(result, ',', b3);
  end if;
  if b4 is not null then
    set result = CONCAT(result, ',', b4);
  end if;
  if b5 is not null then
    set result = CONCAT(result, ',', b5);
  end if;
  if length(result) = 0 then
    set result = null;
  elseif LEFT(result, 1) = ',' then
    set result = SUBSTR(result, 2);
  end if;
  return result;
END//
DELIMITER ;

select mapbehaviors('first','second','third','fourth','fifth');
select mapbehaviors('first',null,null,null,null);
select mapbehaviors('first',null,'third','fourth','fifth');
select mapbehaviors('first',null,'third','fourth',null);
select mapbehaviors(null,'second','third','fourth','fifth');
select mapbehaviors(null,null,null,null,null);
